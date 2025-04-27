from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader
from llm import llm  

# Load the text data (knowledge base)
loader = TextLoader("../knowledge/knowledge_base.txt", encoding="utf-8")
documents = loader.load()

# Set up OpenAI embeddings for document retrieval
embeddings = OpenAIEmbeddings()

# Create a vector store to store document embeddings
vector_store = FAISS.from_documents(documents, embeddings)

# Initialize memory to store conversation context
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# Create the ConversationalRetrievalChain with memory
conversation_chain = ConversationalRetrievalChain.from_llm(
    llm=llm,
    retriever=vector_store.as_retriever(),
    memory=memory,
    verbose=True
)

def get_answer(query: str):
    try:
        # Add the user query as a user message in the memory
        memory.chat_memory.add_user_message(query)

        # Correct the input format by passing the query under the 'question' key
        result = conversation_chain.invoke({"question": query})

        # Check if 'answer' exists in the result and extract it
        if isinstance(result, dict) and 'answer' in result:
            answer = result['answer']
        else:
            return "Sorry, I couldn't get an answer for you at the moment."

        # Add the AI response to memory
        memory.chat_memory.add_ai_message(answer)

        return answer
    except Exception as e:
        print(f"Error occurred while getting an answer: {e}")
        return "Sorry, I couldn't get an answer for you at the moment."

# Test query
# if __name__ == "__main__":
#     # Test with a sample question
#     test_question = "What can you tell me about the PartSelect part with ID PS11766800?"
#     print("\nQuery: ", test_question)
#     print("\nResponse: ", get_answer(test_question))

#     # Test conversation memory by adding another query
#     test_question_2 = "Can you give me more details?"
#     print("\nQuery: ", test_question_2)
#     print("\nResponse: ", get_answer(test_question_2))
