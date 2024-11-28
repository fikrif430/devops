import requests
import psutil
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
import datetime
import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    CallbackContext,
    MessageHandler,
    filters
)
import asyncio
import nest_asyncio


nest_asyncio.apply()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



# Token dan data GitHub
GITHUB_TOKEN = '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'
GITHUB_REPO = 'fikrif430/aplikasi-login'  # Ganti dengan pemilik dan nama repo GitHub Anda
GITHUB_WORKFLOW_ID = 'blank.yml'  # Ganti dengan nama file workflow Anda
ec2_client = boto3.client('ec2', region_name = 'us-east-1')
# Variabel global untuk menyimpan data sementara

# Daftar Key Pair dan AMI ID untuk pemilihan




headers = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json',
}

authorized_users = ["allowed_username"]  # Ganti dengan username Telegram yang diizinkan

{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "ec2:StopInstances",
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": "ec2:DescribeInstances",
            "Resource": "*"
        }
    ]
}

# Teks bantuan /help
HELP_TEXT = """
🛠️ **Daftar Command dan Fungsinya**:

/help - Menampilkan daftar command ini.
/deploy - Menjalankan workflow GitHub Actions (Deploy).
/status - Mengecek status workflow GitHub Actions.
/server_status - Mengecek status server atau instance cloud.
/stop - menghentikan instance yang berjalan.
/stop_all - menghentikan semua instance yang berjalan.
/start_instance - Menjalankan instance yang berhenti.
/startall_instance - Menjalankan semua instance yang berhenti.
"""

# Fungsi untuk menjalankan workflow GitHub Actions (Deploy)
async def deploy(update: Update, context):
    user = update.effective_user.username
    if user not in authorized_users:
        await update.message.reply_text("Anda tidak memiliki izin untuk menjalankan perintah ini.")
        return

    url = f'https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{GITHUB_WORKFLOW_ID}/dispatches'
    data = {"ref": "main"}  # Branch yang ingin dijalankan

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 204:
        await update.message.reply_text('Deploy berhasil dijalankan di GitHub Actions!')
    else:
        await update.message.reply_text(f'Gagal menjalankan deploy. Status: {response.status_code}')

# Fungsi untuk cek status workflow GitHub Actions
async def status(update: Update, context):
    url = f'https://api.github.com/repos/{GITHUB_REPO}/actions/runs'
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        runs = response.json()['workflow_runs']
        if runs:
            last_run = runs[0]
            status_message = (f"Workflow terakhir: {last_run['name']}\n"
                              f"Status: {last_run['status']}\n"
                              f"Hasil: {last_run['conclusion']}")
            await update.message.reply_text(status_message)
        else:
            await update.message.reply_text('Tidak ada workflow yang ditemukan.')
    else:
        await update.message.reply_text(f'Gagal mengecek status workflow. Status: {response.status_code}')

# Fungsi untuk menampilkan daftar perintah
async def help_command(update: Update, context):
    await update.message.reply_text(HELP_TEXT)

# Fungsi untuk cek status server
# async def server_status(update: Update, context):
#     # Dummy response - Sesuaikan dengan API monitoring Anda
#     server_status = "Server running (CPU: 20%, RAM: 45%)"
#     await update.message.reply_text(f"📡 Status Server:\n{server_status}")

# Fungsi untuk menampilkan metrik sistem
async def all_instance_metrics(update: Update, context):
    region = 'us-east-1'  # Tentukan region yang ingin digunakan
    try:
        # Inisialisasi klien CloudWatch dan EC2
        cloudwatch = boto3.client('cloudwatch', region_name=region)
        ec2 = boto3.client('ec2', region_name=region)

        # Ambil daftar semua instance di region ini
        response = ec2.describe_instances()
        instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instances.append(instance['InstanceId'])

        # Memeriksa status metrics untuk setiap instance
        metrics_status = []
        for instance_id in instances:
            print(f"Memeriksa metrics untuk Instance: {instance_id}")  # Debug log

            # Ambil data CPU utilization untuk instance
            cpu_metric = cloudwatch.get_metric_statistics(
                Period=300,  # Data interval 5 menit
                StartTime=datetime.datetime.utcnow() - datetime.timedelta(minutes=10),
                EndTime=datetime.datetime.utcnow(),
                MetricName='CPUUtilization',
                Namespace='AWS/EC2',
                Statistics=['Average'],
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}]
            )

            # Ambil data Disk I/O untuk instance
            disk_metric = cloudwatch.get_metric_statistics(
                Period=300,  # Data interval 5 menit
                StartTime=datetime.datetime.utcnow() - datetime.timedelta(minutes=10),
                EndTime=datetime.datetime.utcnow(),
                MetricName='DiskReadOps',
                Namespace='AWS/EC2',
                Statistics=['Sum'],
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}]
            )

            # Memeriksa jika data tersedia
            cpu_utilization = cpu_metric['Datapoints']
            disk_ops = disk_metric['Datapoints']

            if cpu_utilization and disk_ops:
                cpu_avg = cpu_utilization[0]['Average']
                disk_ops_sum = disk_ops[0]['Sum']

                # Menyusun pesan untuk tiap instance
                metrics_status.append(
                    f"📍 *Instance ID:* {instance_id}\n"
                    f"*CPU Utilization (Rata-rata 10 menit terakhir):* {cpu_avg:.2f}%\n"
                    f"*Disk Read Operations (10 menit terakhir):* {disk_ops_sum}\n"
                    f"-----------------------------"
                )
            else:
                print(f"Tidak ada data metrik untuk Instance {instance_id}")  # Debug log

        if metrics_status:
            await update.message.reply_text(
                f"📊 *Metrics Semua Instance di Region {region}:*\n\n" + "\n\n".join(metrics_status),
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(f"Tidak ada data metrics yang ditemukan di region {region}.")

    except Exception as e:
        await update.message.reply_text(f"Terjadi kesalahan: {e}")
        print(f"Error: {e}")  # Debug log


# Fungsi untuk memulai bot
async def start(update: Update, context):
    await update.message.reply_text('Halo! Saya chatbot DevOps Anda. Gunakan /help untuk melihat daftar perintah.')
    await update.message.reply_text('Halo! Gunakan /stop <instance_id> untuk menghentikan instance EC2.')


# Fungsi untuk restricted command
async def restricted_command(update: Update, context):
    user = update.effective_user.username
    if user not in authorized_users:
        await update.message.reply_text("Anda tidak memiliki izin untuk menjalankan perintah ini.")
        return
    await update.message.reply_text("Perintah dijalankan oleh pengguna terotorisasi.")

# Fungsi untuk mengecek status instance di AWS EC2
# Fungsi untuk mengecek status semua instance di AWS EC2
async def server_status(update: Update, context):
    region = 'us-east-1'
    try:
        # Inisialisasi client EC2
        ec2 = boto3.client('ec2', region_name=region)

        # Menyimpan status semua instance
        instance_status = []

        # Gunakan pagination untuk mengambil semua instance
        paginator = ec2.get_paginator('describe_instances')
        for page in paginator.paginate():
            for reservation in page['Reservations']:
                for instance in reservation['Instances']:
                    instance_id = instance['InstanceId']
                    state = instance['State']['Name']
                    instance_type = instance['InstanceType']
                    public_ip = instance.get('PublicIpAddress', 'N/A')
                    launch_time = instance['LaunchTime'].strftime('%Y-%m-%d %H:%M:%S')

                    # Menambahkan informasi instance dalam format rapi
                    instance_status.append(
                        f"*Instance ID:* {instance_id}\n"
                        f"*Status:* {state}\n"
                        f"*Instance Type:* {instance_type}\n"
                        f"*Public IP:* {public_ip}\n"
                        f"*Launch Time:* {launch_time}\n"
                        f"-----------------------------"
                    )
        # Kirim status instance ke pengguna
        if instance_status:
            status_message = "\n".join(instance_status)
            await update.message.reply_text(f"📡 Status Semua Instance Region {region}:\n\n{status_message}")
        else:
            await update.message.reply_text("Tidak ada instance yang ditemukan.")

    except NoCredentialsError:
        await update.message.reply_text("AWS credentials tidak ditemukan. Pastikan telah dikonfigurasi.")
    except PartialCredentialsError:
        await update.message.reply_text("AWS credentials tidak lengkap. Periksa konfigurasi Anda.")
    except Exception as e:
        await update.message.reply_text(f"Terjadi kesalahan: {e}")

async def stop_instance(update: Update, context):
    try:
        # Ambil Instance ID dari perintah (misalnya: /stop i-xxxxxxxxxxxxxxx)
        instance_id = context.args[0]

        # Menghentikan instance menggunakan boto3
        response = ec2_client.stop_instances(InstanceIds=[instance_id])

        # Menyampaikan hasil ke pengguna
        if response['StoppingInstances'][0]['CurrentState']['Name'] == 'stopping':
            await update.message.reply_text(f'Instance {instance_id} sedang dihentikan.')
        else:
            await update.message.reply_text(f'Gagal menghentikan instance {instance_id}.')
    except IndexError:
        # Jika pengguna tidak memberikan instance ID
        await update.message.reply_text('Harap berikan Instance ID, misalnya: /stop i-xxxxxxxxxxxxxxx')
    except Exception as e:
        # Menangani kesalahan umum
        await update.message.reply_text(f'Terjadi kesalahan: {str(e)}')

async def stop_all_instances(update: Update, context):
    region = 'us-east-1'
    try:
        # Ambil semua instance yang berjalan
        response = ec2_client.describe_instances(
            Filters=[
                {
                    'Name': 'instance-state-name',
                    'Values': ['running']  # Hanya instance yang sedang berjalan
                }
            ]
        )
        
        # Ambil Instance ID dari setiap instance yang ditemukan
        instance_ids = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_ids.append(instance['InstanceId'])
        
        # Jika ada instance yang ditemukan
        if instance_ids:
            # Menghentikan semua instance
            stop_response = ec2_client.stop_instances(InstanceIds=instance_ids)

            # Menyampaikan status penghentian ke pengguna
            stopped_instances = [instance['InstanceId'] for instance in stop_response['StoppingInstances']]
            await update.message.reply_text(f'Berhasil menghentikan instance: {", ".join(stopped_instances)}')
        else:
            await update.message.reply_text('Tidak ada instance yang sedang berjalan untuk dihentikan.')
    except Exception as e:
        # Menangani kesalahan umum
        await update.message.reply_text(f'Terjadi kesalahan: {str(e)}')

async def start_instance(update: Update, context):
    region = 'us-east-1'
    try:
        # Ambil ID instance dari parameter perintah
        instance_id = context.args[0] if context.args else None
        
        if instance_id:
            # Jalankan instance tertentu
            response = ec2_client.start_instances(InstanceIds=[instance_id])
            await update.message.reply_text(f"Instance {instance_id} sedang dijalankan.")
        else:
            await update.message.reply_text("Harap masukkan ID instance yang ingin dijalankan.")

    except Exception as e:
        await update.message.reply_text(f'Terjadi kesalahan: {str(e)}')


# Fungsi untuk menjalankan semua instance yang dihentikan
async def start_all_instances(update: Update, context):
    region = 'us-east-1'
    try:
        # Ambil semua instance yang dihentikan
        response = ec2_client.describe_instances(
            Filters=[{
                'Name': 'instance-state-name',
                'Values': ['stopped']  # Ambil instance yang dalam keadaan stopped
            }]
        )

        # Ambil semua Instance ID dari hasil response
        stopped_instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                stopped_instances.append(instance['InstanceId'])

        if stopped_instances:
            # Jalankan semua instance yang dihentikan
            ec2_client.start_instances(InstanceIds=stopped_instances)
            await update.message.reply_text(f"Semua instance yang dihentikan sedang dijalankan: {', '.join(stopped_instances)}")
        else:
            await update.message.reply_text("Tidak ada instance yang dihentikan untuk dijalankan.")

    except Exception as e:
        await update.message.reply_text(f'Terjadi kesalahan: {str(e)}')

# Atur data user di awal
 # Menyimpan data user untuk setiap pengguna


# Mulai proses pembuatan instance
# Fungsi untuk memulai pembuatan instance


async def start_create_instance(update: Update, context):
    """Memulai proses pembuatan instance dengan meminta nama instance."""
    user_id = update.message.from_user.id
    USER_STATE[user_id] = "waiting_for_name"  # Menyimpan status pengguna
    await update.message.reply_text("Masukkan nama untuk instance EC2 Anda:")

USER_STATE = {}  # Menyimpan status pengguna
user_data = {}  # Menyimpan data terkait instance yang sedang dibuat

async def handle_instance_name(update: Update, context: CallbackContext):
    """Menghandle input nama instance."""
    user_id = update.message.from_user.id

    # Pastikan status pengguna adalah "waiting_for_name" sebelum melanjutkan
    logger.info(f"User {user_id} status: {USER_STATE.get(user_id)}")  # Log status pengguna
    if USER_STATE.get(user_id) != "waiting_for_name":
        await update.message.reply_text("Proses pembuatan instance sudah selesai atau tidak valid.")
        return

    instance_name = update.message.text.strip()

    if not instance_name:
        await update.message.reply_text("Nama instance tidak boleh kosong. Silakan masukkan nama yang valid.")
        return

    # Simpan nama instance
    user_data[user_id] = {"name": instance_name}
    USER_STATE[user_id] = "waiting_for_region"  # Update status ke waiting_for_region

    logger.info(f"User {user_id} memilih nama instance: {instance_name}")

    # Tampilkan pilihan region
    regions = ["us-east-1", "us-west-1", "ap-southeast-1"]
    keyboard = [
        [InlineKeyboardButton(region, callback_data=f"region_{region}")]
        for region in regions
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Pilih region untuk instance EC2 Anda:", reply_markup=reply_markup)

async def handle_region_and_keypair(update: Update, context: CallbackContext):
    """Menghandle pemilihan region dan menampilkan daftar KeyPair."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    logger.info(f"User {user_id} status: {USER_STATE.get(user_id)}")  # Log status pengguna
    if USER_STATE.get(user_id) != "waiting_for_region":
        await query.edit_message_text("Proses pembuatan instance sudah selesai atau tidak valid.")
        return

    region = query.data.split("_")[1]
    user_data[user_id]["region"] = region
    USER_STATE[user_id] = "waiting_for_keypair"  # Update status ke waiting_for_keypair

    logger.info(f"User {user_id} memilih region: {region}")

    # Mendapatkan daftar KeyPair dari region yang dipilih
    try:
        ec2 = boto3.client("ec2", region_name=region)
        response = ec2.describe_key_pairs()
        key_pairs = response.get("KeyPairs", [])

        if not key_pairs:
            await query.edit_message_text("Tidak ada KeyPair yang tersedia. Silakan buat KeyPair terlebih dahulu di AWS.")
            return

        # Tampilkan pilihan KeyPair
        keyboard = [
            [InlineKeyboardButton(key["KeyName"], callback_data=f"keypair_{key['KeyName']}")]
            for key in key_pairs
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Pilih KeyPair untuk instance EC2 Anda:", reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error saat mengambil KeyPair: {e}")
        await query.edit_message_text(f"Terjadi kesalahan saat mengambil KeyPair: {e}")

async def handle_keypair_selection(update: Update, context: CallbackContext):
    """Menghandle pilihan KeyPair."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if USER_STATE.get(user_id) != "waiting_for_keypair":
        await query.edit_message_text("Proses pembuatan instance sudah selesai atau tidak valid.")
        return

    keypair = query.data.split("_")[1]
    user_data[user_id]["keypair"] = keypair
    USER_STATE[user_id] = "waiting_for_ami"  # Update status ke waiting_for_ami

    logger.info(f"User {user_id} memilih KeyPair: {keypair}")

    await query.edit_message_text("Masukkan kata kunci untuk mencari AMI dengan format: /search_ami <kata_kunci>")

async def search_ami(update: Update, context: CallbackContext):
    """Mencari AMI berdasarkan kata kunci."""
    user_id = update.message.from_user.id
    if user_id not in user_data or "region" not in user_data[user_id]:
        await update.message.reply_text("Region belum dipilih. Mulai ulang proses dengan /create_instance.")
        return

    if len(context.args) == 0:
        await update.message.reply_text("Gunakan perintah ini dengan format: /search_ami <kata_kunci>")
        return

    keyword = " ".join(context.args)
    region = user_data[user_id]["region"]
    ec2 = boto3.client("ec2", region_name=region)

    try:
        await update.message.reply_text(f"Mencari AMI dengan kata kunci '{keyword}' di region {region}...")

        response = ec2.describe_images(Owners=["amazon"])
        images = [
            image for image in response.get("Images", [])
            if keyword.lower() in image.get("Name", "").lower()
        ]

        if not images:
            await update.message.reply_text(f"Tidak ada AMI ditemukan untuk kata kunci '{keyword}'.")
            return

        images.sort(key=lambda x: x["CreationDate"], reverse=True)
        results = images[:3]

        keyboard = [
            [InlineKeyboardButton(f"{img['Name']} ({img['ImageId']})", callback_data=f"ami_{img['ImageId']}")]
            for img in results
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Hasil pencarian AMI:", reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error saat mencari AMI: {e}")
        await update.message.reply_text(f"Terjadi kesalahan saat mencari AMI: {e}")

async def handle_ami_id(update: Update, context: CallbackContext):
    """Menghandle pilihan AMI ID."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    ami_id = query.data.split("_")[1]

    user_data[user_id]["ami_id"] = ami_id
    USER_STATE[user_id] = "waiting_for_instance_type"  # Update status ke waiting_for_instance_type

    # Menampilkan pilihan tipe instance (misalnya t2.micro, t2.medium, dsb)
    instance_types = ["t2.micro", "t2.small", "t2.medium", "t3.micro", "t3.small"]
    keyboard = [
        [InlineKeyboardButton(itype, callback_data=f"instance_type_{itype}")]
        for itype in instance_types
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"AMI ID telah dipilih: {ami_id}\n\n"
        "Pilih tipe instance yang akan digunakan:",
        reply_markup=reply_markup
    )

async def handle_instance_type(update: Update, context: CallbackContext):
    """Menghandle pilihan tipe instance."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    instance_type = query.data.split("_")[2]

    user_data[user_id]["instance_type"] = instance_type
    USER_STATE[user_id] = "waiting_for_confirmation"  # Update status ke waiting_for_confirmation

    # Konfirmasi data sebelum pembuatan instance
    await query.edit_message_text(
        f"Konfirmasi data berikut:\n"
        f"Nama Instance: {user_data[user_id]['name']}\n"
        f"Region: {user_data[user_id]['region']}\n"
        f"KeyPair: {user_data[user_id]['keypair']}\n"
        f"AMI ID: {user_data[user_id]['ami_id']}\n"
        f"Instance Type: {instance_type}\n\n"
        "Apakah Anda yakin ingin membuat instance? (Ketik 'yes' untuk melanjutkan)"
    )

async def handle_confirmation(update: Update, context: CallbackContext):
    """Menangani konfirmasi dari pengguna."""
    user_id = update.message.from_user.id
    confirmation = update.message.text.strip().lower()

    if confirmation == "yes":
        # Jika pengguna mengetik 'yes', lanjutkan dengan pembuatan instance
        await create_instance(update, context)
    elif confirmation == "no":
        # Jika pengguna mengetik 'no', batalkan pembuatan instance
        await update.message.reply_text("Proses pembuatan instance dibatalkan.")
    else:
        # Jika input bukan 'yes' atau 'no', minta konfirmasi ulang
        await update.message.reply_text("Tolong ketik 'yes' untuk melanjutkan atau 'no' untuk membatalkan.")

async def create_instance(update: Update, context: CallbackContext):
    """Membuat instance EC2."""
    user_id = update.message.from_user.id
    confirmation = update.message.text.strip().lower()

    if confirmation == "yes":
        try:
            ec2 = boto3.client("ec2", region_name=user_data[user_id]["region"])
            instance = ec2.run_instances(
                ImageId=user_data[user_id]["ami_id"],
                InstanceType=user_data[user_id]["instance_type"],
                KeyName=user_data[user_id]["keypair"],
                MinCount=1,
                MaxCount=1
            )
            instance_id = instance["Instances"][0]["InstanceId"]
            await update.message.reply_text(f"Instance berhasil dibuat! ID Instance: {instance_id}")
        except Exception as e:
            logger.error(f"Error saat membuat instance: {e}")
            await update.message.reply_text(f"Terjadi kesalahan saat membuat instance: {e}")
    else:
        await update.message.reply_text("Proses pembuatan instance dibatalkan.")


async def main():
    # Gantikan ini dengan Token API dari BotFather
    TOKEN = '7822547487:AAHNEDspeCWzGkngqnr3vK-hgTR-AApvm68'
    application = Application.builder().token(TOKEN).build()
    # Daftarkan handler command
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("deploy", deploy))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("server_status", server_status))
    application.add_handler(CommandHandler("all_metrics", all_instance_metrics))
    application.add_handler(CommandHandler("restricted_command", restricted_command))
    application.add_handler(CommandHandler("stop", stop_instance))
    application.add_handler(CommandHandler("stop_all", stop_all_instances))
    application.add_handler(CommandHandler("start_instance", start_instance))  # Command untuk start instance per-instance
    application.add_handler(CommandHandler("startall_instance", start_all_instances))  # Command untuk start semua instance
# Menambahkan handler
    application.add_handler(CommandHandler("create_instance", start_create_instance))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_instance_name))
    application.add_handler(CallbackQueryHandler(handle_region_and_keypair, pattern="^region_"))
    application.add_handler(CallbackQueryHandler(handle_keypair_selection, pattern="^keypair_"))
    application.add_handler(CallbackQueryHandler(handle_ami_id, pattern="^ami_"))
    application.add_handler(CommandHandler("search_ami", search_ami))
    application.add_handler(CallbackQueryHandler(handle_instance_type, pattern="^instance_type_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_confirmation))
    

        # Menambahkan handler
    


    # Mulai polling untuk menerima pesan
    await application.run_polling()

    # Jalankan bot
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())