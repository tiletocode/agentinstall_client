import yaml
import configparser
import requests
import sys
import subprocess
import os
import getpass
import re
from datetime import datetime

def check_path_permissions(path):
    """
    경로가 존재하고 읽기/쓰기 권한이 있는지 확인합니다.

    Args:
        path (str): 확인할 경로

    Returns:
        dict: 결과를 나타내는 딕셔너리
            - "exists": 경로 존재 여부 (True/False)
            - "permission": "read", "write", "read-write", 또는 "none"
    """
    exists = os.path.exists(path)
    if not exists:
        return {"exists": False, "permission": "none"}

    readable = os.access(path, os.R_OK)
    writable = os.access(path, os.W_OK)

    if readable and writable:
        permission = "read-write"
    elif readable:
        permission = "read"
    elif writable:
        permission = "write"
    else:
        permission = "none"

    return {"exists": True, "permission": permission}

def create_javaagent_conf(file_path, license_code, server_host, server_port, weaving, logsink, option_string=""):
    """
    :param file_path: 생성할 파일 경로
    :param license_code: license 값
    :param server_host: whatap.server.host 값 (기본값: 빈 문자열)
    """
    try:
        # 현재 시간: 나노초
        created_time = datetime.now().strftime('%s%f')  # 초와 마이크로초를 합친 나노초 표현

        option_string = option_string.replace("|", "\n")

        # 파일 내용 생성
        content = f"""license={license_code}
whatap.server.host={server_host}
whatap.server.port={server_port}

weaving={weaving}
logsink_enabled={logsink}
{option_string}

"""
        # 디렉토리 확인 및 생성
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # 파일 쓰기
        with open(file_path, "w") as conf_file:
            conf_file.write(content)

        print(f"파일 생성 완료: {file_path}")
        print("내용:")
        print(content)

    except Exception as e:
        print(f"파일 생성 중 오류 발생: {e}")

def create_whatap_env(was_dir, config, option_string=""):
    java_base_dir = config['agent']['java_base_dir']
    env_content = f"""WHATAP_HOME={java_base_dir}
WHATAP_JAR=`ls ${{WHATAP_HOME}}/whatap.agent-*.jar | sort -V | tail -1`
WHATAP_OPTS="${{WHATAP_OPTS}} -javaagent:${{WHATAP_JAR}}"
WHATAP_OPTS="${{WHATAP_OPTS}} -Dwhatap.name=`hostname`"
{option_string}
"""
    # env.sh 파일 경로 생성
    file_path = os.path.join(was_dir, "whatap_env.sh")

    # 파일 작성
    with open(file_path, "w") as file:
        file.write(env_content)

    os.chmod(file_path, 0o755)
    print(f"whatap_env.sh 파일이 생성되었습니다: {file_path}")


def create_db_conf(file_path, license_code, server_host, server_port, dbms, db_addr, db_port, object_name, option_string=""):
    """
    :param file_path: 생성할 파일 경로
    :param license_code: license 값
    :param server_host: whatap.server.host 값 (기본값: 빈 문자열)
    """
    try:
        # 현재 시간: 나노초
        created_time = datetime.now().strftime('%s%f')  # 초와 마이크로초를 합친 나노초 표현

        # 파일 내용 생성
        content = f"""license={license_code}
whatap.server.host={server_host}
whatap.server.port={server_port}
object_name={object_name}

dbms={dbms}
{option_string}
db_ip={db_addr}
db_port={db_port}
"""

        # 디렉토리 확인 및 생성
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # 파일 쓰기
        with open(file_path, "w") as conf_file:
            conf_file.write(content)

        print(f"파일 생성 완료: {file_path}")
        print("내용:")
        print(content)

    except Exception as e:
        print(f"파일 생성 중 오류 발생: {e}")

def create_infra_conf(file_path, license_code, server_host, server_port):
    """
    /usr/whatap/infra/conf/whatap.conf 파일을 생성합니다.

    :param file_path: 생성할 파일 경로
    :param license_code: license 값
    :param server_host: whatap.server.host 값 (기본값: 빈 문자열)
    """
    try:
        # 현재 시간: 나노초
        created_time = datetime.now().strftime('%s%f')  # 초와 마이크로초를 합친 나노초 표현

        # 파일 내용 생성
        content = f"""license={license_code}
whatap.server.host={server_host}
whatap.server.port={server_port}
createdtime={created_time}"""

        # 디렉토리 확인 및 생성
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # 파일 쓰기
        with open(file_path, "w") as conf_file:
            conf_file.write(content)

        print(f"파일 생성 완료: {file_path}")
        print("내용:")
        print(content)

    except Exception as e:
        print(f"파일 생성 중 오류 발생: {e}")

def install_deb_package(deb_file_path):
    """
    .deb 패키지를 설치합니다.

    :param deb_file_path: .deb 파일 경로
    """
    try:
        print(f"{deb_file_path} 설치 중...")
        # dpkg 명령 실행
        subprocess.run(["sudo", "dpkg", "-i", deb_file_path], check=True)
        print("INFRA Agent 설치 완료")
    except subprocess.CalledProcessError as e:
        print(f"설치 중 오류 발생: {e}")
    except FileNotFoundError:
        print("dpkg 명령이 시스템에 설치되어 있지 않습니다. 설치 후 다시 시도하세요.")


def extract_tar_gz(file_path, output_dir):
    """
    .tar.gz 파일을 지정된 디렉토리에 압축 해제합니다.

    :param file_path: .tar.gz 파일 경로
    :param output_dir: 압축 해제할 디렉토리 경로
    """
    try:
        subprocess.run(["tar", "-zxvf", file_path, "--no-same-owner"], cwd=output_dir, check=True)
    except Exception as e:
        print(f"압축 해제 실패: {e}")


def download_file_with_progress(url, output_path):
    """
    HTTP를 통해 파일을 다운로드하며 진행률을 표시합니다.

    :param url: 파일의 URL
    :param output_path: 저장할 파일 경로
    """
    try:
        # HTTP GET 요청
        response = requests.get(url, stream=True)
        response.raise_for_status()  # HTTP 오류가 발생하면 예외 처리

        # 파일 크기 가져오기
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0  # 다운로드된 데이터 크기

        # 파일 다운로드
        with open(output_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
                    downloaded_size += len(chunk)

                    # 진행률 계산 및 표시
                    percent = (downloaded_size / total_size) * 100 if total_size > 0 else 0
                    sys.stdout.write(f"\r진행률: {percent:.2f}%")
                    sys.stdout.flush()

        print("\n파일 다운로드 완료:", output_path)

    except requests.exceptions.RequestException as e:
        print(f"파일 다운로드 실패: {e}")

def get_dbx_file(directory):
    # 파일 이름 패턴 정규식 (버전 번호 추출)
    pattern = r"whatap\.agent\.dbx-(\d+\.\d+\.\d+)\.jar"

    # 가장 높은 버전을 저장할 변수
    latest_version = None
    latest_file = None

    # 디렉터리 내 파일 검색
    for filename in os.listdir(directory):
        match = re.match(pattern, filename)
        if match:
            # 버전 번호 추출
            version = tuple(map(int, match.group(1).split(".")))
            if latest_version is None or version > latest_version:
                latest_version = version
                latest_file = filename

    # 최신 파일이 있다면 리턴, 없으면 None을 리턴
    return latest_file


def subproc_uid(java_bin_path, uid_dir, user_id, user_password):
    try:
        dbx_file_path = get_dbx_file(uid_dir)
        #java -cp $EXE_DBX_JAR whatap.dbx.DbUser -update -uid $WUID -user $WUSER -password $WPASSWORD
        subprocess.run([java_bin_path, "-cp", dbx_file_path, "whatap.dbx.DbUser", "-update", "-uid", "1000", "-user", user_id, "-password", user_password], cwd=uid_dir, check=True)
        print("uid  완료")
    except subprocess.CalledProcessError as e:
        print(f"uid  오류 발생: {e}")

def subproc_mv(source_dir, dest_dir):
    try:
        subprocess.run(["mv", source_dir, dest_dir], check=True)
        print(f"mv 완료: {dest_dir}")
    except subprocess.CalledProcessError as e:
        print(f"mv 오류 발생: {e}")


def subproc_startd(dest_dir):
    try:
        subprocess.run(["sh", "startd.sh"], cwd=dest_dir, check=True)
        print("start 완료")
    except subprocess.CalledProcessError as e:
        print(f"start 오류 발생: {e}")


def infra_agent_start():
    try:
        subprocess.run(["sudo", "systemctl", "restart", "whatap-infra.service"], check=True)
        print("restart 완료")
    except subprocess.CalledProcessError as e:
        print(f"restart 오류 발생: {e}")


# YAML 파일 읽기
def load_yaml_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as yaml_file:
        data = yaml.safe_load(yaml_file)
    return data



# Platform 선택

def select_platform(data):
    platforms = sorted(set(item['Platform'] for item in data))  # Platform 목록 추출

    print("사용 가능한 Platform 목록:")
    for idx, platform in enumerate(platforms, start=1):
        print(f"{idx}. {platform}")

    while True:
        try:
            choice = int(input("Platform 번호를 선택하세요: "))
            if 1 <= choice <= len(platforms):
                return list(platforms)[choice - 1]
            else:
                print("유효한 번호를 선택하세요.")
        except ValueError:
            print("숫자를 입력하세요.")

# Name (ProjectCode) 선택
def select_name(data, selected_platform):
    filtered_projects = [
        {'Name': item['Name'], 'ProjectCode': item['ProjectCode'], 'LicenseKey': item.get('LicenseKey')}
        for item in data if item['Platform'] == selected_platform
    ]
    print(f"\n{selected_platform} Platform에 해당하는 프로젝트 목록:")
    for idx, project in enumerate(filtered_projects, start=1):
        print(f"{idx}. {project['Name']} ({project['ProjectCode']})")

    while True:
        try:
            choice = int(input("프로젝트 번호를 선택하세요: "))
            if 1 <= choice <= len(filtered_projects):
                return filtered_projects[choice - 1]
            else:
                print("유효한 번호를 선택하세요.")
        except ValueError:
            print("숫자를 입력하세요.")

def infra_agent_install(config, license_key):
    default_base_dir = config['agent']['temp_base_dir']
    agent_url = config['front']['base_url'] + config['front']['infra_agent_path']

    temp_base_dir = ""
    print("")
    print("=== INFRA Agent 다운로드 ===")
    user_temp_base_dir = input(f"INFRA Agent 다운로드할 경로를 입력하세요 (default : {default_base_dir}) : ")
    if user_temp_base_dir.strip() == "":
        temp_base_dir = default_base_dir
    else:
        temp_base_dir = user_temp_base_dir.strip()

    path_permission = check_path_permissions(temp_base_dir)

    if path_permission["permission"] != "read-write":
        print(f"'{temp_base_dir}' 경로가 존재하지 않거나 read-write 권한이 없습니다.")
        sys.exit(1)  # 비정상 종료

    agent_tar_path = temp_base_dir + "/agent.deb"
    download_file_with_progress(agent_url, agent_tar_path)
    print("")
    print("=== INFRA Agent 설치 ===")
    install_deb_package(agent_tar_path)

    server_host = config['agent']['server_host']
    server_port = config['agent']['infra_server_port']
    print("")
    print("=== whatap.conf 파일 생성 ===")
    create_infra_conf("/usr/whatap/infra/conf/whatap.conf", license_key, server_host, server_port)
    print("")
    print("=== Agent 재기동 ===")
    infra_agent_start()


def select_logging_framework():
    print("Log 프레임워크 종류를 입력하세요.")
    print("1. logback-1.2.8 이상")
    print("2. log4j-2.17 이상")
    print("3. 해당사항 없음")
    

    while True:
        try:
            user_input = input("번호를 입력하세요: ").strip()
            if user_input == "1":
                return "logback-1.2.8 "
            elif user_input == "2":
                return "log4j-2.17 "
            elif user_input == "3":
                return ""
            else:
                print("잘못된 입력입니다. ")
        except Exception as e:
            print(f"오류 발생: {e}")



def select_in_list(items, weaving_msg):
    """
    설정에서 버전 목록을 읽고 사용자가 선택하도록 구현합니다.
    버전 목록이 없을 경우 "" 반환.

    Args:
        config (dict): 설정 데이터가 포함된 딕셔너리

    Returns:
        str or float: 선택한 버전 (숫자) 또는 빈 문자열 ("")
    """
    
    available_items = [item.strip() for item in items.split(",")]

    # 버전 목록이 없으면 빈 문자열 반환
    if not available_items:
        print("No items available.")
        return ""

    while True:
        try:
            user_input = input(weaving_msg + " [" + items + "] : ")

            if user_input in available_items:
                return user_input
            else:
                print("목록에 값이 없습니다. 다시 입력하세요.")
        except ValueError:
            print("목록에 값이 없습니다. 다시 입력하세요.")



def java_agent_install(config, license_key):
    default_base_dir = config['agent']['temp_base_dir']
    agent_url = config['front']['base_url'] + config['front']['java_agent_path']

    temp_base_dir = ""
    print("")
    print("=== JAVA Agent 다운로드 ===")
    user_temp_base_dir = input(f"JAVA Agent 다운로드할 경로를 입력하세요 (default : {default_base_dir}) : ")
    if user_temp_base_dir.strip() == "":
        temp_base_dir = default_base_dir
    else:
        temp_base_dir = user_temp_base_dir.strip()

    path_permission = check_path_permissions(temp_base_dir)

    if path_permission["permission"] != "read-write":
        print(f"'{temp_base_dir}' 경로가 존재하지 않거나 read-write 권한이 없습니다.")
        sys.exit(1)  # 비정상 종료

    agent_tar_path = temp_base_dir + "/java_agent.tar.gz"
    
    download_file_with_progress(agent_url, agent_tar_path)
    print("")
    print("=== JAVA Agent 압축 해제 ===")
    extract_tar_gz(agent_tar_path, temp_base_dir)

    java_agent_dir = config['agent']['java_base_dir']

    print("")
    print("== JAVA Agent 설치 디렉토리 지정 ===")
    subproc_mv(temp_base_dir + "/whatap", java_agent_dir)

    server_host = config['agent']['server_host']
    server_port = config['agent']['java_server_port']

    # print("로그모니터링 유무를 입력하세요: ")
    print("")
    print("=== whatap.conf 옵션 지정 ===")
    weaving_logsink_msg = "로그모니터링 유무를 입력하세요"
    logsink_str = select_in_list("true, false", weaving_logsink_msg)
    logsink_enabled = logsink_str


    weaving_items = []

    # print("아래 항목 중 Spring Boot 버전을 입력하세요. (Spring Boot가 아닐 경우 N/A로 입력)")
    springboot_avail_version = config['agent']['springboot_versions'] + ", N/A"
    weaving_springboot_msg = "Spring boot 버전을 입력하세요. (Spring boot이 아닐 경우 N/A로 입력)"
    spring_boot_ver = select_in_list(springboot_avail_version, weaving_springboot_msg)
    if spring_boot_ver != "N/A":
        weaving_items.append("spring-boot-" + spring_boot_ver)

    logframework_ver = select_logging_framework()
    if logframework_ver != "":
        weaving_items.append(logframework_ver)

    weaving_string =  ",".join(weaving_items)


    deafault_apm_config_contents = config['agent']['deafault_apm_config_contents']
    create_javaagent_conf(java_agent_dir + "/whatap.conf", license_key, server_host, server_port, weaving_string, logsink_enabled, deafault_apm_config_contents)


    option_string=""

    print("=== Agent 실행 옵션 지정 ===")
   

     
    while True:
        was_dir=input("WAS 또는 Spring boot 실행경로는 입력하세요.(ex: /app/esg_main/bin) : ")
        was_dir_permission = check_path_permissions(was_dir)
        if was_dir_permission["permission"] != "read-write":
            print(f"'{was_dir}' 경로가 존재하지 않거나 read-write 권한이 없습니다.")
        else:
            break

    jvm_version=select_in_list("yes, no", "java 실행 version이  17 이상입니까?")
    if jvm_version== "yes":
        jvm_reflect_opt =  select_in_list("yes, no", "java 실행시 REFLECT Options (--add-opens=java.base/java.lang=ALL-UNNAMED) 이 포함되어 있습니까?")
        if jvm_reflect_opt == "no":
            option_string = 'WHATAP_OPTS="${WHATAP_OPTS} --add-opens=java.base/java.lang=ALL-UNNAMED"'


    create_whatap_env(was_dir, config, option_string)
    print("application 실행환경에서 source whatap_env.sh를 실행한 후 인스턴스 실행 스크립트에 java $WHATAP_OPTS 를 추가하시면 java agent가 추가됩니다.") 

def db_agent_install(config, license_key, platform):
    default_base_dir = config['agent']['db_base_dir']
    db_agent_url = config['front']['base_url'] + config['front']['db_agent_path']
    jdbc_path = platform.lower() + "_jdbc_path"
    if platform in {"MYSQL", "POSTGRESQL", "MSSQL"}:
        jdbc_url = config['front']['base_url'] + config['front'][jdbc_path]
    
    print("")
    print("=== DB Agent 다운로드 ===")
    temp_base_dir=""
    user_temp_base_dir = input(f"DB Agent 다운로드할 경로를 입력하세요 (default : {default_base_dir}) : ")
    if user_temp_base_dir.strip() == "":
        temp_base_dir = default_base_dir
    else:
        temp_base_dir = user_temp_base_dir.strip()

    path_permission = check_path_permissions(temp_base_dir)

    if path_permission["permission"] != "read-write":
        print(f"'{temp_base_dir}' 경로가 존재하지 않거나 read-write 권한이 없습니다.")
        sys.exit(1)  # 비정상 종료

    agent_tar_path = temp_base_dir + "/db_agent.tar.gz"
    agent_jdbc_path = temp_base_dir + "/" + platform.lower() + ".jar"

    download_file_with_progress(db_agent_url, agent_tar_path)
    if platform in {"MYSQL", "POSTGRESQL", "MSSQL"}:
        download_file_with_progress(jdbc_url, agent_jdbc_path)
    print("")
    print("=== DB 접속정보 입력 ===")
    instance_name  = input("DB Server 이름을  입력하세요(DB Agent Dir) : ")
    db_addr  = input("DB Addr을 입력하세요 : ")
    db_port  = input("DB Port을 입력하세요 : ")
    user_id  = input("DB User을 입력하세요 : ")
    user_password  = getpass.getpass("DB Password을 입력하세요 : ")

    option_string = ""
    if platform in {"POSTGRESQL", "MSSQL"}:
        db_name = input("모니터링 대상 DB Name을 입력하세요 : ")
        option_string = "db=" + db_name
    object_name  = input("DB 서비스 이름을  입력하세요(Agent Name) : ")

    server_host = config['agent']['server_host']
    server_port = config['agent']['db_server_port']

    print("")
    print("=== DB Agent 압축 해제 ===")
    extract_tar_gz(agent_tar_path, temp_base_dir)
    dest_dir = temp_base_dir + "/" + instance_name
    print("")
    print("== DB Agent 설치 디렉토리 지정 ===")
    subproc_mv(temp_base_dir + "/whatap", temp_base_dir + "/" + instance_name)
    if platform in {"MYSQL", "POSTGRESQL", "MSSQL"}:
        subproc_mv(agent_jdbc_path, dest_dir + "/jdbc")
    
    print("")
    print("=== whatap.conf 파일 생성 ===")
    create_db_conf(dest_dir + "/whatap.conf", license_key, server_host, server_port, platform.lower(), db_addr, db_port, object_name, option_string)
    
    print("")
    print("=== UID 파일 생성 ===")
    subproc_uid(config['db_agent_env']['java_bin_path'], dest_dir, user_id, user_password)
    print("")
    print("=== DB Agent 기동 ===")
    subproc_startd(dest_dir)



# 대화형 프로그램 실행
def main():

    config = configparser.ConfigParser()
    config.read("installer.ini", encoding='utf-8')

    front_base_url = config['front']['base_url']
    project_path = config['front']['project_path']

    print("")
    print("=== 프로젝트 메타데이터 다운로드 ===")
    download_file_with_progress(front_base_url + project_path, "project.yaml")

    yaml_file_path = "project.yaml"
    data = load_yaml_file(yaml_file_path)

    print("")
    print("=== 설치 프로그램 선택 ===")
    selected_platform = select_platform(data)
    selected_project = select_name(data, selected_platform)

    print("")
    print("=== 선택된 항목 ===")
    print(f"Platform: {selected_platform}")
    print(f"Name: {selected_project['Name']}")
    print(f"ProjectCode: {selected_project['ProjectCode']}")

    # LicenseCode 출력
    if selected_project.get('LicenseKey'):
        print(f"LicenseKey: {selected_project['LicenseKey']}")
    else:
        print("LicenseKey가 존재하지 않습니다.")


    if selected_platform == "INFRA":
        infra_agent_install(config, selected_project['LicenseKey'])
    elif selected_platform in {"MYSQL", "REDIS", "POSTGRESQL"}:
        db_agent_install(config, selected_project['LicenseKey'], selected_platform)
    elif selected_platform == "JAVA":
        java_agent_install(config, selected_project['LicenseKey'])

if __name__ == "__main__":
    main()