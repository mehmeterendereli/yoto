import os

def create_video(video_files, audio_file, output_file, title, description):
    try:
        # Çıktı dizinini oluştur
        output_dir = os.path.dirname(output_file)
        os.makedirs(output_dir, exist_ok=True)

        # Her video için filtreleri hazırla
        filter_chains = []
        for i in range(len(video_files)):
            # Her video için 10 saniyelik kesit al ve ölçeklendir
            filter_chain = f"[{i}:v]trim=0:10,setpts=PTS-STARTPTS,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}]"
            filter_chains.append(filter_chain)

        # Video girişlerini birleştir
        concat_inputs = ''.join(f'[v{i}]' for i in range(len(video_files)))
        concat_filter = f"{concat_inputs}concat=n={len(video_files)}:v=1:a=0[vconcated]"

        # Tüm filtreleri birleştir
        filter_complex = ';'.join(filter_chains + [concat_filter])

        # FFmpeg komutunu oluştur
        input_args = []
        for video_file in video_files:
            input_args.extend(['-i', video_file])
        input_args.extend(['-i', audio_file])

        cmd = [
            config.FFMPEG_PATH,
            '-y',
            *input_args,
            '-filter_complex', filter_complex,
            '-map', '[vconcated]',
            '-map', f'{len(video_files)}:a',
            '-c:v', 'h264_nvenc',
            '-preset', 'p4',
            '-rc:v', 'vbr',
            '-b:v', '5M',
            '-maxrate:v', '10M',
            '-bufsize:v', '10M',
            '-r', '30',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-b:a', '192k',
            output_file
        ]

        # Komutu çalıştır
        subprocess.run(cmd, check=True)

    except Exception as e:
        print(f"Video oluşturma hatası: {e}")
        return False

    return True 