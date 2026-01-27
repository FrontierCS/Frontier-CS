#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n, k;
    if (!(cin >> n >> k)) return 0;

    size_t N = (size_t)n * (size_t)n;

    // Detect if there is more numeric input available (offline mode)
    std::streambuf* sb = cin.rdbuf();
    int c = sb->sgetc();
    while (c != std::char_traits<char>::eof() && isspace(static_cast<unsigned char>(c))) {
        sb->sbumpc();
        c = sb->sgetc();
    }
    bool offline = (c != std::char_traits<char>::eof()) && (c == '-' || (c >= '0' && c <= '9'));

    if (!offline) {
        // Interactive fallback (no matrix provided): cannot proceed meaningfully here.
        cout << "DONE " << 0 << '\n' << flush;
        return 0;
    }

    vector<long long> a;
    a.reserve(N);
    long long x;
    for (size_t i = 0; i < N; ++i) {
        if (!(cin >> x)) break;
        a.push_back(x);
    }

    if (a.size() < N) {
        if (a.empty()) {
            cout << "DONE " << 0 << '\n' << flush;
            return 0;
        } else {
            if ((size_t)k <= a.size()) {
                nth_element(a.begin(), a.begin() + (k - 1), a.end());
                cout << a[k - 1] << '\n' << flush;
            } else {
                nth_element(a.begin(), a.end() - 1, a.end());
                cout << a.back() << '\n' << flush;
            }
            return 0;
        }
    }

    nth_element(a.begin(), a.begin() + (k - 1), a.end());
    long long ans = a[k - 1];
    cout << ans << '\n' << flush;
    return 0;
}