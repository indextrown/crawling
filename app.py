from flask import Flask, render_template_string
from flask_caching import Cache
from apscheduler.schedulers.background import BackgroundScheduler
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service  # Selenium의 Chrome Service 임포트
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from datetime import datetime, timedelta
import re
import psutil
import time
from selenium.common.exceptions import WebDriverException

app = Flask(__name__)

# 캐시 설정: 데이터를 메모리에 캐시하고, 60초 동안 유효
app.config['CACHE_TYPE'] = 'simple'  # 간단한 캐시 방식 (메모리)
app.config['CACHE_DEFAULT_TIMEOUT'] = 60  # 캐시의 기본 만료 시간 (60초)
cache = Cache(app)

# 주기적으로 크롤링을 실행할 스케줄러 설정
scheduler = BackgroundScheduler()

# 현재 시간 (한국 시간 기준)
current_time = datetime.now()

## 드라이버 최적화
def driver_Settings():
    options = Options()

    # 웹드라이버 종료 안시키고 유지
    #options.add_experimental_option("detach", True)

    # 주석해제하면 헤드리스 모드
    options.add_argument("--headless")  # 헤드리스 모드로 실행

    # Windows 10 운영 체제에서 Chrome 브라우저를 사용하는 것처럼 보이는 사용자 에이전트가 설정
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    # 언어 설정을 한국어로 지정. 이는 웹 페이지가 한국어로 표시
    options.add_argument('lang=ko_KR')

    # GPU 가속을 비활성화. GPU 가속이 활성화되어 있으면, Chrome이 GPU를 사용하여 그래픽을 렌더링하려고 시도할 수 있기때문. 일부 환경에서는 GPU 가속이 문제를 일으킬 수 있으므로 이 옵션을 사용하여 비활성화
    options.add_argument('--disable-gpu')

    # 정보 표시줄을 비활성화. 정보 표시줄은 Chrome 브라우저 상단에 나타나는 알림이나 메시지를 의미. 이 옵션을 사용하여 이러한 알림이 나타나지 않도록 설정.
    options.add_argument('--disable-infobars')

    # 확장 프로그램을 비활성화. Chrome에서 확장 프로그램을 사용하지 않도록 설정
    options.add_argument('--disable-extensions')

    #  자동화된 기능을 비활성화. 이 옵션은 Chrome이 자동화된 환경에서 실행되는 것을 감지하는 것을 방지
    options.add_argument('--disable-blink-features=AutomationControlled')

    # 자동화를 비활성화. 이 옵션은 Chrome이 자동화 도구에 의해 제어되는 것으로 감지되는 것을 방지
    options.add_argument('--disable-automation')

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    except WebDriverException as e:
        print(f"웹 드라이버 시작 중 오류가 발생했습니다: {e}")
        return None
    return driver

# 크롤링 데이터의 시간을 파싱하는 함수
def parse_time_info(time_info):
    time_patterns = {
        "시간 전": r"(\d+)\s*시간 전",
        "분 전": r"(\d+)\s*분 전",
        "일 전": r"(\d+)\s*일 전",
        "주 전": r"(\d+)\s*주 전",
        "개월 전": r"(\d+)\s*개월 전",
        "년 전": r"(\d+)\s*년 전",
        "날짜": r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.",
    }
    for unit, pattern in time_patterns.items():
        match = re.match(pattern, time_info)
        if match:
            if unit == "시간 전":
                return current_time - timedelta(hours=int(match.group(1)))
            elif unit == "분 전":
                return current_time - timedelta(minutes=int(match.group(1)))
            elif unit == "일 전":
                return current_time - timedelta(days=int(match.group(1)))
            elif unit == "주 전":
                return current_time - timedelta(weeks=int(match.group(1)))
            elif unit == "개월 전":
                return current_time - timedelta(days=int(match.group(1)) * 30)
            elif unit == "년 전":
                return current_time - timedelta(days=int(match.group(1)) * 365)
            elif unit == "날짜":
                year, month, day = map(int, match.groups())
                return datetime(year, month, day)
    return None

# 크롤링 함수에 재시도 로직 추가
def crawl_data():
    data = []  # 데이터를 저장할 리스트
    search = "추락"  # 검색할 키워드
    page_nums = 5  # 검색할 페이지 수
    days_back = 0  # 오늘만 크롤링

    # 오늘 자정부터 수집 시작
    if days_back == 0:
        start_date = current_time.replace(hour=0, minute=0, second=0, microsecond=0)  # 오늘 자정
    else:
        start_date = current_time - timedelta(days=days_back)  # 특정 날짜부터 수집

    driver = driver_Settings()  # 웹 드라이버 설정

    if not driver:
        return []

    for page_num in range(0, page_nums * 10, 10):
        try:
            driver.get(f"https://www.google.com/search?q={search}&tbm=nws&start={page_num}")
            posts = driver.find_elements(By.CSS_SELECTOR, "#rso > div > div > div")  # 게시글 요소 추출

            for post in posts:
                try:
                    post_info = post.find_elements(By.CSS_SELECTOR, "div > div > a > div > div:nth-child(2) > div")
                    company = post_info[0].text if len(post_info) > 0 else "Unknown"
                    title = post_info[1].text if len(post_info) > 1 else "Unknown"
                    content = post_info[2].text if len(post_info) > 2 else "Unknown"
                    time_info = post_info[-1].text if len(post_info) > 0 else "Unknown"
                    post_url = post.find_element(By.CSS_SELECTOR, "div > div > a").get_attribute("href")
                    
                    # 시간 계산
                    calculated_time = parse_time_info(time_info)
                    
                    # 날짜 필터링: start_date와 비교하여 수집할 데이터인지 확인
                    if calculated_time >= start_date and calculated_time <= current_time:
                        data.append({
                            "Company": company,
                            "Title": title,
                            "Content": content,
                            "Link": post_url,
                            "Calculated_time": calculated_time,
                        })

                except Exception as e:
                    print(f"Error processing post: {e}")

        except Exception as e:
            print(f"Error accessing page {page_num}: {e}")
            time.sleep(5)  # 5초 대기 후 재시도

    driver.quit()  # 드라이버 종료

    # 프로세스 종료
    terminate_process_by_name("chrome")  # 크롬 프로세스를 종료하는 함수

    # 데이터를 pandas DataFrame으로 변환
    df = pd.DataFrame(data, columns=["Company", "Title", "Content", "Link", "Calculated_time"])

    # `Calculated_time` 기준으로 최신순 정렬
    df = df.sort_values(by="Calculated_time", ascending=False)

    # `Calculated_time`을 '년-월-일 시:분' 형식으로 변환
    df['Calculated_time'] = df['Calculated_time'].apply(lambda x: x.strftime("%Y-%m-%d %H:%M"))

    return df.to_dict(orient='records')  # 데이터를 딕셔너리 형태로 반환

# 크롬 프로세스를 종료하는 함수
def terminate_process_by_name(process_name):
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if process_name.lower() in proc.info['name'].lower():
                print(f"Terminating process {proc.info['name']} with PID {proc.info['pid']}")
                proc.terminate()  # 프로세스 종료
                proc.wait()  # 종료 대기
                print(f"Process {proc.info['name']} terminated successfully")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass  # 예외 처리


# 크롤링 데이터를 캐시하고, 1분마다 갱신
@cache.cached(timeout=60, key_prefix="crawl_data")
def get_cached_data():
    return crawl_data()  # 캐시된 데이터 반환

# 1분마다 캐시된 데이터를 갱신하는 함수
def update_cache():
    cache.delete('crawl_data')  # 캐시 삭제
    get_cached_data()  # 새로운 데이터를 크롤링하여 캐시 갱신
    print("갱신되었습니다")  # 갱신 완료 메시지 출력

# 주기적으로 크롤링 작업을 실행하도록 스케줄러에 작업 추가
scheduler.add_job(func=update_cache, trigger="interval", minutes=1)
scheduler.start()  # 스케줄러 시작

# 웹 페이지에서 크롤링 결과를 출력하는 함수
@app.route('/')
def index():
    data = get_cached_data()  # 캐시된 데이터 가져오기

    # 데이터를 HTML로 변환하여 웹 페이지로 출력
    return render_template_string("""
        <html>
            <head>
                <title>크롤링 결과</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        background-color: #f4f4f9;
                        margin: 0;
                        padding: 0;
                    }
                    h1 {
                        text-align: center;
                        color: #333;
                        margin-top: 30px;
                    }
                    table {
                        width: 80%;
                        margin: 30px auto;
                        border-collapse: collapse;
                        background-color: #fff;
                        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                        border-radius: 15px;  /* 테이블의 꼭짓점을 둥글게 설정 */
                        overflow: hidden;  /* 둥근 모서리 안에 내용이 들어가도록 처리 */
                    }
                    th, td {
                        padding: 12px;
                        text-align: left;
                        border-bottom: 1px solid #ddd;
                    }
                    # th {
                    #     background-color: #007BFF;
                    #     color: white;
                    # }
                    th {
                        background-color: #000;  /* 테이블 헤더 배경색을 검은색으로 설정 */
                        color: white;  /* 글자 색을 흰색으로 설정 */
                    }
                    tr:nth-child(even) {
                        background-color: #f2f2f2;
                    }
                    a {
                        color: #007BFF;
                        text-decoration: none;
                    }
                    a:hover {
                        text-decoration: underline;
                    }
                </style>
            </head>
            <body>
                <h1>오늘의 이슈 Monitoring</h1>
                <table>
                    <thead>
                        <tr>
                            <th>Company</th>
                            <th>Title</th>
                            <th>Content</th>
                            <th>Link</th>
                            <th>Calculated Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for row in data %}
                            <tr>
                                <td>{{ row['Company'] }}</td>
                                <td>{{ row['Title'] }}</td>
                                <td>{{ row['Content'] }}</td>
                                <td><a href="{{ row['Link'] }}" target="_blank">Link</a></td>
                                <td>{{ row['Calculated_time'] }}</td>
                            </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </body>
        </html>
    """, data=data)  # 데이터를 HTML로 변환하여 출력

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

