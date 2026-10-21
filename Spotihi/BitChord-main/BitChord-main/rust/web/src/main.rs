use leptos::*;
use leptos_router::*;

#[component]
fn App() -> impl IntoView {
    view! {
        <Router>
            <main>
                <Routes>
                    <Route path="/" view=HomePage />
                    <Route path="/search" view=SearchPage />
                    <Route path="/library" view=LibraryPage />
                </Routes>
            </main>
        </Router>
    }
}

#[component]
fn HomePage() -> impl IntoView {
    view! {
        <div class="spotihi-home">
            <h1>"SpotiHi"</h1>
            <p>"Your music, your way."</p>
        </div>
    }
}

#[component]
fn SearchPage() -> impl IntoView {
    view! {
        <div class="spotihi-search">
            <h1>"Search"</h1>
            <input type="text" placeholder="Search for songs, artists, albums..." />
        </div>
    }
}

#[component]
fn LibraryPage() -> impl IntoView {
    view! {
        <div class="spotihi-library">
            <h1>"Library"</h1>
            <p>"Your playlists and saved music."</p>
        </div>
    }
}

fn main() {
    console_error_panic_hook::set_once();
    mount_to_body(App);
}