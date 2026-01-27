#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) return 0;
    if (!s1.empty() && s1.back() == '\r') s1.pop_back();
    if (!s2.empty() && s2.back() == '\r') s2.pop_back();

    size_t n = s1.size(), m = s2.size();
    size_t k = min(n, m);

    auto write_n = [](char c, size_t cnt) {
        const size_t B = 1 << 20;
        static vector<char> buf(B);
        fill(buf.begin(), buf.end(), c);
        while (cnt > 0) {
            size_t chunk = min(cnt, B);
            fwrite(buf.data(), 1, chunk, stdout);
            cnt -= chunk;
        }
    };

    // Write k 'M's
    write_n('M', k);

    if (n > m) {
        write_n('D', n - m);
    } else if (m > n) {
        write_n('I', m - n);
    }

    // Newline at the end
    fputc('\n', stdout);
    fflush(stdout);
    return 0;
}