<?php
function get_all_auto_data($plaka) {
    $url = "https://auto.bir23.com/az/searchCar?country_id=1&plateNumber=" . urlencode($plaka);
    $html = file_get_contents($url);
    if (!$html) return [[], [], [], ["tiktok" => "Yox", "instagram" => "Yox", "whatsapp" => "Yox"]];

    libxml_use_internal_errors(true);
    $dom = new DOMDocument();
    @$dom->loadHTML($html);
    $xpath = new DOMXPath($dom);

    $imgs = [];
    $videos = [];
    $infos = [];
    $socials = ["tiktok" => "Yox", "instagram" => "Yox", "whatsapp" => "Yox"];

    // Resimler
    foreach ($xpath->query("//img") as $img) {
        $src = $img->getAttribute("src");
        if (strpos($src, "/images/cars/") !== false || strpos($src, "/az/cars/") !== false || strpos($src, "medias/photos") !== false) {
            $imgs[] = $src;
        }
    }

    // Videolar
    foreach ($xpath->query("//video | //video/source") as $video) {
        $src = $video->getAttribute("src");
        if (strpos($src, "/images/cars/") !== false || strpos($src, "/az/cars/") !== false || strpos($src, "medias/photos") !== false) {
            $videos[] = $src;
        }
    }

    // Bilgi tablosu
    foreach ($xpath->query("//tr") as $tr) {
        $tds = $tr->getElementsByTagName("td");
        if ($tds->length == 2) {
            $key = trim($tds[0]->nodeValue);
            $val = trim($tds[1]->nodeValue);
            $infos[$key] = $val;
        }
    }

    // Sosyal medya
    foreach ($xpath->query("//a") as $a) {
        $href = $a->getAttribute("href");
        $class = $a->getAttribute("class");

        if (strpos($class, "tiktok-gradient") !== false) $socials["tiktok"] = $href;
        if (strpos($class, "insta-gradient") !== false) $socials["instagram"] = $href;
        if (strpos($class, "wp-gradient") !== false) $socials["whatsapp"] = $href;
    }

    return [$imgs, $videos, $infos, $socials];
}

// Veriyi al
$plaka = $_GET["plaka"] ?? "";
$images = $videos = $infos = [];
$socials = ["tiktok" => "Yox", "instagram" => "Yox", "whatsapp" => "Yox"];
$message = "";

if ($plaka) {
    list($images, $videos, $infos, $socials) = get_all_auto_data($plaka);
    if (empty($images) && empty($videos) && empty($infos)) {
        $message = "Plaka '{$plaka}' üçün məlumat tapılmadı :(";
    }
}
?>

<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Plaka Axtarışı</title>
    <style>
        body {
            background: #111;
            color: white;
            text-align: center;
            font-family: sans-serif;
            padding: 20px;
        }
        .led {
            display: inline-block;
            background: black;
            color: cyan;
            border: 2px solid cyan;
            padding: 10px;
            margin: 10px;
            border-radius: 10px;
        }
        input, button {
            padding: 10px;
            font-size: 16px;
            margin: 5px;
            border-radius: 6px;
        }
        .message {
            margin-top: 20px;
            color: #f66;
            font-weight: bold;
        }
        table td {
            background: #222;
            color: #0ff;
            border: 1px solid #555;
            padding: 5px;
        }
    </style>
</head>
<body>
    <h1>🚗 CekaMods Maşın Axtarış Sistemi</h1>
    <form method="get">
        <input class="led" name="plaka" placeholder="Məs: 10FF110" required value="<?= htmlspecialchars($plaka) ?>">
        <button class="led" type="submit">Axtar</button>
    </form>

    <?php foreach ($images as $img): ?>
        <div class="led"><img src="<?= $img ?>" style="max-width:90%; border-radius:10px; max-height:300px;"></div>
    <?php endforeach; ?>

    <?php foreach ($videos as $vid): ?>
        <div class="led">
            <video controls style="max-width:90%; border-radius:10px; max-height:300px;">
                <source src="<?= $vid ?>" type="video/mp4">
            </video>
        </div>
    <?php endforeach; ?>

    <?php if ($infos): ?>
        <table style="margin: 20px auto; border-collapse: collapse;">
            <?php foreach ($infos as $k => $v): ?>
                <tr><td><?= $k ?></td><td><?= $v ?></td></tr>
            <?php endforeach; ?>
        </table>
    <?php endif; ?>

    <div style="margin-top: 20px;">
        <div class="led"><b>TikTok:</b> <?= $socials['tiktok'] ?></div>
        <div class="led"><b>Instagram:</b> <?= $socials['instagram'] ?></div>
        <div class="led"><b>WhatsApp:</b> <?= $socials['whatsapp'] ?></div>
    </div>

    <div class="message"><?= $message ?></div>
</body>
</html>
