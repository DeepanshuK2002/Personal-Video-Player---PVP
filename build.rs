use std::env;
use std::path::Path;

fn main() {
    let out = env::var("OUT_DIR").unwrap();
    let ico_path = Path::new(&out).join("logo.ico");

    let opts = usvg::Options::default();
    let tree = usvg::Tree::from_str(include_str!("assets/logo.svg"), &opts).expect("parse svg");
    let size: u32 = 256;
    let mut pixmap = tiny_skia::Pixmap::new(size, size).expect("pixmap");
    let scale = size as f32 / tree.size().width().max(tree.size().height());
    resvg::render(&tree, tiny_skia::Transform::from_scale(scale, scale), &mut pixmap.as_mut());

    let img = image::RgbaImage::from_raw(size, size, pixmap.data().to_vec()).expect("image");
    img.save_with_format(&ico_path, image::ImageFormat::Ico)
        .expect("save ico");

    let mut res = winres::WindowsResource::new();
    res.set_icon(ico_path.to_str().unwrap());
    res.compile().expect("compile resources");
}
