from pageindex import PageIndexClient
 
pi_client = PageIndexClient(api_key="2cd460c1ab594e63b97ee000c4a05b7f")

result = pi_client.submit_document("/Users/jinyiw/Documents/claude-projects/deep_research_agent/contracts/反馈0730-【已审查】（190号）互联网类系统CDN加速服务（三年）采购合同HT-ZRUB-2025-07-01-08-C002.docx.pdf")
doc_id = result["doc_id"]
status = pi_client.get_document(doc_id)["status"]
if status == "completed":
    print('File processing completed')