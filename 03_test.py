# 작업에 필요한 패키지를 불러옵니다
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime, timedelta
import re
import pandas as pd

# 현재 시각 (한국 시간 기준)
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

    # 브라우저 창의 크기를 지정. 여기서는 너비 430px, 높이 932px로 설정
    options.add_argument('--window-size=932,932')

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

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    return driver

# 시간 정보를 계산하는 함수
def parse_time_info(time_info):
    """
    Parse time info like '6시간 전', '1주 전', or '2024. 10. 23.' and return the calculated datetime.
    """
    # 정규표현식 패턴
    time_patterns = {
        "시간 전": r"(\d+)\s*시간 전",
        "분 전": r"(\d+)\s*분 전",
        "일 전": r"(\d+)\s*일 전",
        "주 전": r"(\d+)\s*주 전",
        "개월 전": r"(\d+)\s*개월 전",
        "년 전": r"(\d+)\s*년 전",
        "날짜": r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.",
    }

    # 상대적 시간 계산
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

    # 파싱 실패 시 None 반환
    return None

driver = driver_Settings()

# 날짜 지정 변수 추가(예: 오늘부터 7일 전까지 수집)
days_back = 0  # 오늘만 수집
current_time = datetime.now()  # 현재 시간

# days_back이 0일 때만 오늘 날짜를 사용하고, 다른 경우는 timedelta를 사용하여 범위를 설정
if days_back == 0:
    start_date = current_time.replace(hour=0, minute=0, second=0, microsecond=0)  # 오늘 자정
else:
    start_date = current_time - timedelta(days=days_back)

# 원하는 페이지 수
page_nums = 5
search = "추락"

# 데이터를 저장할 리스트
data = []

# 0, 10, 20, 30
# Google 검색 결과에서 데이터 수집
for page_num in range(0, page_nums * 10, 10):
    driver.get(f"https://www.google.com/search?q={search}&sca_esv=1f2f2e42c8b63453&tbm=nws&sxsrf=ADLYWIJiMdOV1vEJqiO9AKtDvtz5QmvpWA:1735375337578&ei=6blvZ473Itu3vr0P08HGyA0&start={page_num}&sa=N&ved=2ahUKEwjOj7H0iMqKAxXbm68BHdOgEdk4FBDy0wN6BAgEEAQ&biw=933&bih=973&dpr=1.8")
    posts = driver.find_elements(By.CSS_SELECTOR, "#rso > div > div > div")

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
                # 데이터 저장
                data.append({
                    "Company": company,
                    "Title": title,
                    "Content": content,
                    "Link": post_url,
                    "Calculated_time": calculated_time,
            
                })
            
            # 결과 출력
            # print(f"URL: {post_url} | Original Time: {time_info} | Calculated Time: {calculated_time}")
            # print(f"URL: {post_url} | Calculated Time: {calculated_time}")

        except Exception as e:
            print(f"Error processing post: {e}")

# 데이터 정렬: calculated_time 기준 최신순 정렬
try:
    # 정렬 시 이미 datetime인 경우 그대로 사용
    datas = sorted(data, key=lambda x: x["Calculated_time"] if isinstance(x["Calculated_time"], datetime) 
    else datetime.strptime(x["Calculated_time"], "%Y-%m-%d %H:%M:%S"), reverse=True)
except ValueError as e:
    print(f"Date parsing error: {e}")
except TypeError as e:
    print(f"Type error: {e}")


for data in datas:
    print(data)
# python3 "/Users/kimdonghyeon/크롤링/크롤링 자동화/03_test.py"

import psutil

# 종료하려는 프로세스 이름
process_name = "chrome"  # 또는 "Google Chrome" (운영체제에 따라 다를 수 있음)

# 모든 프로세스를 조회하여 이름이 'chrome'인 프로세스를 종료
for proc in psutil.process_iter(['pid', 'name']):
    try:
        # 프로세스 이름이 chrome인지 확인
        if process_name.lower() in proc.info['name'].lower():
            print(f"Terminating process {proc.info['name']} with PID {proc.info['pid']}")
            proc.terminate()  # 프로세스 종료
            proc.wait()  # 종료가 완료될 때까지 대기
            print(f"Process {proc.info['name']} terminated successfully")
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass  # 프로세스가 이미 종료되었거나 권한이 없을 경우 예외 처리
