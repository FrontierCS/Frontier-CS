#include <bits/stdc++.h>
using namespace std;

static inline void appendInt(string &out, int x) {
    if (x == 0) { out.push_back('0'); return; }
    char buf[16];
    int n = 0;
    while (x > 0) {
        buf[n++] = char('0' + (x % 10));
        x /= 10;
    }
    while (n--) out.push_back(buf[n]);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    if (n <= 3) {
        cout << 0 << "\n";
        return 0;
    }

    int B = 1;
    while (1LL * B * B * B < (long long)n) B <<= 1;

    vector<pair<int,int>> tasks; // (L, split)
    int maxSmall = min(n, B - 1);
    for (int L = 2; L <= maxSmall; L++) tasks.push_back({L, L - 1});

    if (B > 1 && B <= n) tasks.push_back({B, B / 2});

    for (int k = 2; k <= B - 1; k++) {
        int L = k * B;
        if (L <= n) tasks.push_back({L, L - B});
    }

    int BB = B * B;
    if (B > 1 && BB <= n) tasks.push_back({BB, BB / 2});

    for (int k = 2; k <= B - 1; k++) {
        int L = k * BB;
        if (L <= n) tasks.push_back({L, L - BB});
    }

    long long m = 0;
    for (auto [L, split] : tasks) {
        (void)split;
        m += (long long)(n + 1 - L);
    }

    string out;
    out.reserve((size_t)min<long long>(m, 300000LL) * 18ULL + 32ULL);

    appendInt(out, (int)m);
    out.push_back('\n');

    for (auto [L, split] : tasks) {
        for (int u = 0; u + L <= n; u++) {
            int c = u + split;
            int v = u + L;
            appendInt(out, u); out.push_back(' ');
            appendInt(out, c); out.push_back(' ');
            appendInt(out, v); out.push_back('\n');
        }
    }

    cout << out;
    return 0;
}