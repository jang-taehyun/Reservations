from flask import Flask, request, jsonify
import boto3
import re

app = Flask(__name__)

# Bedrock 클라이언트 초기화
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name='ap-northeast-1')

def retrieve_and_generate_keyword(query, kbId, modelArn, numberOfResults, keywordPromptTemplate):
    response = bedrock_agent_runtime.retrieve_and_generate(
        input={'text': query},
        retrieveAndGenerateConfiguration={
            'type': 'KNOWLEDGE_BASE',
            'knowledgeBaseConfiguration': {
                'knowledgeBaseId': kbId,
                'modelArn': modelArn,
                'retrievalConfiguration': {
                    'vectorSearchConfiguration': {
                        'numberOfResults': numberOfResults
                    }
                },
                'generationConfiguration': {
                    'promptTemplate': {
                        'textPromptTemplate': keywordPromptTemplate
                    }
                }
            }
        }
    )
    return response

def retrieve_and_generate_query(query, kbId, modelArn, numberOfResults, queryPromptTemplate):
    response = bedrock_agent_runtime.retrieve_and_generate(
        input={'text': query},
        retrieveAndGenerateConfiguration={
            'type': 'KNOWLEDGE_BASE',
            'knowledgeBaseConfiguration': {
                'knowledgeBaseId': kbId,
                'modelArn': modelArn,
                'retrievalConfiguration': {
                    'vectorSearchConfiguration': {
                        'numberOfResults': numberOfResults
                    }
                },
                'generationConfiguration': {
                    'promptTemplate': {
                        'textPromptTemplate': queryPromptTemplate
                    }
                }
            }
        }
    )
    return response

def parse_bookstore_info(text):
    bookstores = []
    pattern = r'\d+\.\s+\*\*책방 이름:\*\*\s*(.*?)\s*\*\*위치:\*\*\s*(.*?)\s*\*\*설명:\*\*\s*(.*?)(?=\d+\.\s+\*\*책방 이름:|$)'
    matches = re.findall(pattern, text, re.DOTALL)
    
    for match in matches:
        bookstores.append({
            "FCLTY_NM": match[0].strip(),
            "FCLTY_ROAD_NM_ADDR": match[1].strip(),
            "describe": match[2].strip()
        })
    
    return bookstores

@app.route('/recommend', methods=['POST'])
def retrieve_endpoint():
    data = request.json
    query = data.get('query')
    isKeyword = data.get('keyword')
    numberOfResults = data.get('numberOfResults', 3)  # 기본값 3으로 설정
    kbId = 'OE7ZVODU7F'  # 지식 기반 ID를 직접 설정
    modelArn = 'arn:aws:bedrock:ap-northeast-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0'  # 모델 ARN
    
    if not query:
        return jsonify({"error": "Query is required"}), 400

    # 동적으로 출력 형식 생성
    output_format = '\n'.join([f"{i+1}. **책방 이름:** [이름]\n   **위치:** [위치]\n   **설명:** [기본 설명 및 해당 책방에 대한 종합적인 평가를 포함해주세요. 특히 쿼리와의 관련성, 특징, 추천 이유 등을 언급해주세요.]" for i in range(numberOfResults)])

    # 키워드 기반 한국어로 된 사용자 정의 프롬프트 템플릿
    keywordPromptTemplate = f"""
당신은 책방을 찾아주는 도우미입니다. 다음 키워드에 관련된 책방을 찾아주세요: "{query}"

제공된 검색 결과를 사용하여 다음 질문에 답하세요:

**질문:** "{query}" 키워드와 가장 관련 있는 상위 {numberOfResults}개의 책방을 제공해주세요. 각 책방의 이름, 위치, 그리고 그 책방에 대한 설명과 종합적인 평가를 포함해야 합니다.

**검색 결과:** $search_results$

**출력 형식:**

{output_format}

각 책방의 설명에는 기본적인 정보뿐만 아니라, 해당 책방에 대한 종합적인 평가도 포함해주세요. 특히 쿼리와의 관련성, 책방의 특징, 추천 이유 등을 언급해주세요. 모든 정보는 한 단락 안에 통합하여 제공해주세요.

사용자에게 다양한 옵션을 제공하기 위해 책방들이 서로 다른지 확인하세요. 응답을 작성할 때는 검색 결과에서 제공된 정보만을 사용하세요.

창의적이고 다양한 방식으로 책방을 소개해주세요. 각 책방의 고유한 특징과 매력을 강조하여 설명해주세요.
"""
    
    # 쿼리 기반 한국어로 된 사용자 정의 프롬프트 템플릿
    queryPromptTemplate = f"""
당신은 책방을 찾아주는 도우미입니다. 다음 요구사항에 맞는 책방을 찾아주세요: "{query}"

제공된 검색 결과를 사용하여 다음 질문에 답하세요:

**질문:** 요구사항은 다음과 같습니다. "{query}" 요구사항에 맞는 가장 관련 있는 상위 {numberOfResults}개의 책방을 제공해주세요. 각 책방의 이름, 위치, 그리고 그 책방에 대한 설명과 종합적인 평가를 포함해야 합니다.

**검색 결과:** $search_results$

**출력 형식:**

{output_format}

각 책방의 설명에는 기본적인 정보뿐만 아니라, 해당 책방에 대한 종합적인 평가도 포함해주세요. 특히 쿼리와의 관련성, 책방의 특징, 추천 이유 등을 언급해주세요. 모든 정보는 한 단락 안에 통합하여 제공해주세요.

사용자에게 다양한 옵션을 제공하기 위해 책방들이 서로 다른지 확인하세요. 응답을 작성할 때는 검색 결과에서 제공된 정보만을 사용하세요.

창의적이고 다양한 방식으로 책방을 소개해주세요. 각 책방의 고유한 특징과 매력을 강조하여 설명해주세요.
"""
    
    try:
        if(isKeyword == "True"):
            response = retrieve_and_generate_keyword(query, kbId, modelArn, numberOfResults, keywordPromptTemplate)
        else:
            response = retrieve_and_generate_query(query, kbId, modelArn, numberOfResults, queryPromptTemplate)
        # 텍스트 출력을 파싱하여 JSON 형식으로 변환
        output = response.get("output", {}).get("text", "")
        bookstores = parse_bookstore_info(output)
        
        return jsonify(bookstores), 200, {'Content-Type': 'application/json'}
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "The application is running normally"}), 200
    
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
