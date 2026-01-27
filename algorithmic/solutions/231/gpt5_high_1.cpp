#include <bits/stdc++.h>
using namespace std;

#ifdef __unix__
#include <sys/select.h>
#include <unistd.h>
bool inputAvailable() {
    fd_set fds;
    FD_ZERO(&fds);
    FD_SET(STDIN_FILENO, &fds);
    timeval tv;
    tv.tv_sec = 0;
    tv.tv_usec = 0;
    int r = select(STDIN_FILENO + 1, &fds, nullptr, nullptr, &tv);
    return r > 0 && FD_ISSET(STDIN_FILENO, &fds);
}
#else
bool inputAvailable() { return false; }
#endif

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m, T;
    if (!(cin >> n >> m >> T)) return 0;
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
    }

    cout << 0 << '\n';
    cout.flush();

    for (int t = 0; t < T; ++t) {
        cout << "! 1\n";
        cout.flush();

        // Read interactor's response if available to avoid blocking or pipe fill.
        string resp;
        while (inputAvailable()) {
            if (!(cin >> resp)) break;
            if (resp == "Wrong") return 0;
            // Ignore other responses (e.g., "Correct")
        }
    }

    return 0;
}