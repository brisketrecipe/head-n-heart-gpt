import logging
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from dotenv import load_dotenv
from datetime import datetime
import openai
from document_processor import DocumentProcessor
from openai_service import OpenAIService
from storage_service import StorageService
from pinecone_service import PineconeService

# Set up logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

# Import our components
from document_processor import DocumentProcessor
from openai_service import OpenAIService
from storage_service import StorageService
from pinecone_service import PineconeService

# Create FastAPI app
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
document_processor = DocumentProcessor()
openai_service = OpenAIService()
storage_service = StorageService(bucket_name=os.getenv("GCS_BUCKET_NAME"))
pinecone_service = PineconeService()

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        # Read file content
        content = await file.read()
        filename = file.filename
        
        # Process document content and detect type
        extracted_content, filetype = document_processor.extract_content(filename, content)
        
        # Process with OpenAI (chunking and tagging)
        chunks, tags = openai_service.process_document(extracted_content, filename, filetype=filetype)
        
        # Generate embeddings for each chunk
        chunk_objs = []
        for chunk in chunks:
            embedding_response = openai_service.client.embeddings.create(
                input=chunk["text"] if isinstance(chunk, dict) and "text" in chunk else chunk,
                model="text-embedding-ada-002"
            )
            embedding = embedding_response.data[0].embedding
            chunk_objs.append({"text": chunk["text"] if isinstance(chunk, dict) and "text" in chunk else chunk, "embedding": embedding})
        
        # Upsert to Pinecone
        pinecone_service.upsert_chunks(filename, chunk_objs, tags)
        
        # Store in GCS
        gcs_path = storage_service.upload_file(content, filename)
        
        # Store processed results
        processed_data = {
            "filename": filename,
            "gcs_path": gcs_path,
            "chunks": chunks,
            "tags": tags,
            "processed_date": str(datetime.now())
        }
        
        # Store processed data in GCS
        storage_service.store_processed_content(filename, processed_data)
        
        return {
            "filename": filename,
            "chunks_processed": len(chunks),
            "tags": tags,
            "gcs_path": gcs_path
        }
    except Exception as e:
        logging.exception("Error in /upload endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def query_content(request: Request):
    try:
        # Clear the log file
        with open("app.log", "w") as f:
            f.write("")
            
        data = await request.json()
        query = data.get("query", "")
        # Generate embedding for query
        query_embedding_response = openai_service.client.embeddings.create(
            input=query,
            model="text-embedding-ada-002"
        )
        query_embedding = query_embedding_response.data[0].embedding
        # Query Pinecone
        matches = pinecone_service.query(query_embedding, top_k=20)
        # Gather context from top chunks
        chunks = [match["metadata"]["chunkText"] for match in matches]
        context = "\n\n".join(chunks)
        
                # Log each chunk individually with metadata
        logging.info("=== CHUNKS RETRIEVED FROM PINECONE ===")
        for i, match in enumerate(matches):
            logging.info(f"CHUNK {i+1}:")
            logging.info(f"Text: {match['metadata']['chunkText']}")
            # Log any other metadata available in the match
            for key, value in match['metadata'].items():
                if key != 'chunkText':
                    logging.info(f"{key}: {value}")
            logging.info("---")
        logging.info("=== END CHUNKS ===")

        # Log the context and prompt
        logging.info("=== FULL CONTEXT BEING FED TO GPT ===")
        logging.info(context)
        logging.info("=== END CONTEXT ===")
        
        # Use GPT-4o to answer
        messages = [
      {"role": "system", "content": """You are an expert curriculum developer specializing in entrepreneurship education at the Wolff Center for Entrepreneurship (WCE). 

IMPORTANT INSTRUCTIONS FOR EXTRACTING CONTENT:
1. Extract ONLY direct quotes from the provided context. Do NOT paraphrase or summarize.
2. Each chunk may come from different documents - look for a 'filename' field in the chunk metadata if available.
3. If the filename is not explicitly given, refer to the chunk by its content and position (e.g., "Chunk about Law of Curiosity").
4. When providing references, be specific about where in the document the content appears (e.g., section title, page if available).
5. If you can't find an exact location reference, explicitly state "Reference: [Document name], exact location unknown".

Your goal is to provide a structured lesson plan with accurate, directly quoted content and precise source attributions."""},
            {"role": "user", "content": f"""
I need you to analyze the provided context and extract the most relevant material for developing a lesson plan for the Wolff Center for Entrepreneurship (WCE) at the University of Houston's C. T. Bauer College of Business.

The WCE is guided by a philosophy centered on empowering students to understand their values, articulate their dreams, and achieve tangible outcomes. The program emphasizes both academic rigor and real-world application, preparing students to assume leadership roles in business by teaching them how to develop and implement their own ventures. WCE fosters personal and professional growth through mentorship, experiential learning, and a commitment to integrity and innovation.

Our program focuses on four core value categories, each with four specific behavioral competencies:

1. ACTION
   - Results
   - Execution
   - Fearless Presenter
   - Seize Opportunities

2. RELATIONSHIPS
   - Connection
   - Leadership
   - Collaboration
   - Awareness

3. DISCIPLINE
   - Planning
   - Constructive Thinking
   - Organize
   - Control

4. PURPOSE
   - Authenticity
   - CEO Perspective
   - Vision
   - Growth Mindset

For the behavioral competency: {query}

Please extract 8-10 relevant sections from the context, provide precise references for each, and suggest how to incorporate them into our entrepreneurship-focused lesson plan. Each suggestion should specifically reinforce the behavioral competency while aligning with WCE's overall philosophy. Conclude with an overall approach for teaching this competency.

In the reference output, please explicitly mention the filename from the content. It is listed in the metadata at the top of each file as "filename".

The additional user and assistant prompts are only for reference. Do not use them in your response. Please only use use the context provided. Do not assume the lesson plan the user is asking for, allow them to tell you. 

Context:
{context}
"""},
            {"role": "user", "content": "We want to develop a lesson plan on 'Fearless Presenter' for our WCE students. Please extract the relevant material and provide suggestions that align with this behavioral competency under the ACTION core value."},
            {"role": "assistant", "content": """
{
  "competency": "Fearless Presenter",
  "category": "ACTION",
  "extracts": [
    {
      "content": "Effective communication is not merely about slide design or voice projection—it's about conveying conviction in your venture's value proposition. Research indicates that investors make preliminary funding decisions within the first 3 minutes of a pitch, responding primarily to the founder's passionate belief in their solution.",
      "reference": "Entrepreneurial_Communication_Guide.pdf, Chapter 4, 'Pitch Psychology,' Pages 78-82",
      "teaching_suggestion": "Structure a progressive pitching exercise where students present the same concept three times with increasing stakes: first to a peer, then to a small group, and finally to a panel of visiting entrepreneurs. Provide specific feedback on how their conviction comes through in each iteration."
    },
    {
      "content": "Fear management techniques distinguish novice from experienced presenters. The entrepreneurial mindset reframes presentation anxiety as excitement, utilizing physiological arousal as fuel rather than allowing it to become an obstacle to effective delivery.",
      "reference": "Founder_Psychology_Handbook.pdf, Section 5.3, 'Performance Under Pressure'",
      "teaching_suggestion": "Teach specific pre-presentation routines that embrace nervous energy, including power posing, controlled breathing, and positive visualization. Have students develop personalized 5-minute pre-presentation rituals they can implement before important pitches."
    },
    {
      "content": "Story-driven presentations generate 63% better recall than fact-based approaches. The entrepreneurial narrative arc—establishing the problem, revealing the journey to the solution, and painting the vision of impact—creates both emotional connection and logical understanding.",
      "reference": "Pitch_Deck_Development_Manual.pdf, Chapter 2, 'Narrative Structures for Entrepreneurs'",
      "teaching_suggestion": "Challenge students to identify their venture's 'origin story' and craft it into a 2-minute opening that establishes both credibility and emotional resonance before any business metrics are shared."
    },
    {
      "content": "Data visualization literacy separates memorable presentations from forgettable ones. Entrepreneurs must transform complex business information into instantly comprehensible visual insights that support rather than overwhelm their core message.",
      "reference": "Data_Communication_Guide.pdf, Pages 45-51, 'Visual Storytelling for Business Impact'",
      "teaching_suggestion": "Conduct a workshop where students bring their venture's most complex dataset and develop three different visualization approaches, then test which creates the fastest understanding with audience members."
    }
  ],
  "lesson_approach": "To develop 'Fearless Presenter' competency in WCE students, I recommend an immersive approach that integrates technical presentation skills with emotional resilience building. The lesson should begin by addressing the psychological barriers many entrepreneurs face when presenting their ventures, framing fear as a natural response that can be channeled productively. I suggest implementing a 'presentation laboratory' format where students regularly present in increasingly challenging scenarios—from informal peer sessions to formal investor panels with real-world entrepreneurs. Throughout this progression, focus on three pillars: (1) authentic message development that aligns with the student's personal values, (2) strategic presentation design that emphasizes story over slides, and (3) embodied communication techniques that build physical confidence. The most effective approach would culminate in a high-stakes presentation opportunity where students must respond to unexpected challenges or questions, reinforcing WCE's action-oriented philosophy. Consider recording presentations at various stages of development so students can witness their own growth, reinforcing the Growth Mindset competency from the Purpose category while building their confidence as Fearless Presenters."
}

"""},
            {"role": "user", "content": "We want to develop a lesson plan on 'CEO Perspective' for our WCE students. Please extract the relevant material and provide suggestions that align with this behavioral competency under the PURPOSE core value."},
            {"role": "assistant", "content": """

{
  "competency": "CEO Perspective",
  "category": "PURPOSE",
  "extracts": [
    {
      "content": "The CEO Perspective requires entrepreneurs to simultaneously hold three time horizons: immediate tactical execution, mid-range strategic positioning, and long-term vision fulfillment. Research with successful founders reveals that this cognitive flexibility—switching between operational details and big-picture thinking—correlates strongly with venture longevity.",
      "reference": "Executive_Mindset_Manual.pdf, Chapter 3, 'Temporal Leadership Dimensions,' Pages 72-79",
      "teaching_suggestion": "Implement a 'three horizons exercise' where students make decisions about the same business challenge from three different timeframes (next week, next year, next decade), then analyze how these perspectives lead to different priorities and actions."
    },
    {
      "content": "CEO Perspective encompasses the ability to analyze stakeholder ecosystems holistically. Novice entrepreneurs often optimize for customer needs alone, while experienced founders balance the interests of customers, team members, investors, partners, and community with sophisticated tradeoff analysis.",
      "reference": "Stakeholder_Management_Guide.pdf, Section 4.2, 'Multi-constituency Decision Making'",
      "teaching_suggestion": "Create a stakeholder simulation where student teams navigate a complex business decision with actors representing different stakeholders with competing interests. Debrief by evaluating how effectively they balanced diverse needs while staying true to core venture values."
    },
    {
      "content": "The psychological burden of ultimate accountability distinguishes the CEO role from all others. Research on entrepreneur resilience indicates that those who develop rituals for processing failure, celebrating small wins, and maintaining perspective during crises demonstrate significantly higher leadership effectiveness scores.",
      "reference": "Founder_Psychology_Report.pdf, Pages 115-127, 'Decision-Making Under Uncertainty'",
      "teaching_suggestion": "Establish a regular 'CEO reflection practice' where students document their decision processes, assumptions, and emotional responses to outcomes. Partner with the Psychology department to provide structured feedback on their self-awareness and emotional regulation strategies."
    },
    {
      "content": "Houston's most successful entrepreneurs demonstrate a distinct form of CEO Perspective through their ability to connect industry-specific opportunities with broader economic and social trends. This contextual intelligence—seeing how their venture fits within larger systems—enables more strategic resource allocation and more compelling narrative creation.",
      "reference": "Houston_Entrepreneurship_Case_Studies.pdf, Volume 3, 'Systems Thinking in Practice'",
      "teaching_suggestion": "Organize small-group sessions with successful Houston CEOs where students present their analysis of how macro trends impact their specific venture concept, receiving feedback on their contextual intelligence and systems thinking."
    },
    {
      "content": "Financial literacy transforms from a technical skill to a strategic advantage when entrepreneurs develop what veteran CEOs call 'number sense'—the ability to quickly identify which metrics truly drive business health and which are vanity metrics that distract from core value creation.",
      "reference": "Financial_Leadership_for_Entrepreneurs.pdf, Chapter 8, 'From Accounting to Strategy'",
      "teaching_suggestion": "Challenge students to identify the 3-5 most critical metrics for their venture and defend why these specific numbers deserve CEO attention. Have them create a one-page 'CEO Dashboard' that would guide their weekly decision-making."
    }
  ],
  "lesson_approach": "To develop the 'CEO Perspective' competency under the PURPOSE core value, I recommend a lesson approach that balances conceptual understanding with experiential learning. Begin with a session exploring the distinction between management (doing things right) and leadership (doing the right things), using case studies that illustrate how CEO Perspective manifests in entrepreneurial decision-making. The heart of the lesson should utilize a comprehensive business simulation where students rotate through the CEO role, facing escalating challenges that require them to balance competing priorities, make decisions with incomplete information, and communicate their reasoning to various stakeholders. Critical to this approach is structured reflection after each simulation round, where students articulate how their decisions align with both immediate business needs and longer-term vision. Throughout the lesson, deliberately connect CEO Perspective to the other PURPOSE competencies, particularly Vision and Authenticity, showing how effective CEOs maintain alignment between personal values, company mission, and strategic decisions. Consider partnering with the WCE mentorship network to arrange shadow opportunities where students observe real CEOs navigating complex decisions, followed by debrief conversations about the thought processes witnessed. The assessment should evaluate students not on the specific decisions made, but on their ability to articulate comprehensive reasoning that demonstrates holistic understanding of their venture's ecosystem."
}
     
"""},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
        ]
        
        # Log the complete messages being sent to GPT
        logging.info("\n=== COMPLETE MESSAGES BEING SENT TO GPT ===")
        for i, msg in enumerate(messages, 1):
            logging.info(f"\n--- Message {i} ---")
            logging.info(f"Role: {msg['role']}")
            logging.info(f"Content:\n{msg['content']}")
            logging.info("--- End Message ---")
        logging.info("\n=== END MESSAGES ===")
        
        response = openai_service.client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        response_json = response.choices[0].message.content
        try:
            data = json.loads(response_json)
            formatted = f"### Competency: {data.get('competency', '')}  \n**Category:** {data.get('category', '')}\n\n---\n\n#### Extracts\n"
            for i, extract in enumerate(data.get('extracts', []), 1):
                teaching_suggestion = extract.get('teaching_suggestion', '').replace('. ', '.\n   - ')
                formatted += f"{i}. **Content:**  \n   {extract.get('content', '')}  \n   **Reference:**  \n   {extract.get('reference', '')}  \n   **Teaching Suggestion:**  \n   - {teaching_suggestion}\n\n"
            formatted += "---\n\n#### Lesson Approach\n\n" + data.get('lesson_approach', '')
        except Exception:
            formatted = response_json  # fallback to raw if not JSON
        return {"reply": formatted}
    except Exception as e:
        logging.exception("Error in /query endpoint")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"} 