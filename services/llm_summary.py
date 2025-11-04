from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Inisialisasi LLM Google Gemini (atau ganti dengan model lain jika perlu)
# Pastikan environment variable GOOGLE_API_KEY sudah di-set
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)

prompt_template = ChatPromptTemplate.from_template(
    """
    Anda adalah asisten analisis Facebook Ads yang profesional, proaktif, dan komunikatif.
    Berdasarkan hasil agregasi berikut:
    {summary}
    Lakukan analisis tren performa (apakah naik, turun, atau stagnan) dari data tersebut.
    Berikan reasoning (penjelasan logis) atas tren yang Anda temukan.
    Jika performa menurun, berikan analisis penyebab dan saran konkret untuk perbaikan.
    Jika performa naik, berikan insight dan tips optimasi lanjutan agar hasil makin baik.
    Jawaban harus selalu natural, relevan, dan mudah dipahami advertiser Facebook Ads.
    Jangan mengarang jika data tidak tersedia, dan jangan memberikan informasi yang tidak ada di data.
    Jika pertanyaan user tidak bisa dijawab dari data, jawab dengan jujur dan profesional, misal: "Maaf, data yang Anda minta tidak tersedia."
    Akhiri dengan bullet point saran atau rekomendasi jika memungkinkan.
    Pertanyaan user:
    {question}
    """
)

output_parser = StrOutputParser()

def llm_summarize_aggregation(summary: str, question: str) -> str:
    chain = prompt_template | llm | output_parser
    return chain.invoke({"summary": summary, "question": question})
