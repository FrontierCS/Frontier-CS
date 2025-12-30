#include <bits/stdc++.h>
using namespace std;

static inline void appendInt(string &s, int x) {
    if (x == 0) { s.push_back('0'); return; }
    char buf[16];
    int len = 0;
    while (x > 0) {
        buf[len++] = char('0' + (x % 10));
        x /= 10;
    }
    for (int i = len - 1; i >= 0; --i) s.push_back(buf[i]);
}

static string buildConstantQuery(int n, int val) {
    string s;
    s.reserve(3 + 6 + n * 7);
    s.push_back('?');
    s.push_back(' ');
    appendInt(s, n);
    for (int i = 0; i < n; ++i) {
        s.push_back(' ');
        appendInt(s, val);
    }
    s.push_back('\n');
    return s;
}

static int readAnswerOrExit() {
    int x;
    if (!(cin >> x)) exit(0);
    if (x == -1) exit(0);
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int N = 100000;
    const int C = 317;
    const int M = 316;

    string qC = buildConstantQuery(N, C);
    string q1 = buildConstantQuery(N, 1);

    int t;
    if (!(cin >> t)) return 0;

    for (int tc = 0; tc < t; ++tc) {
        // Query 1: N words of length C
        cout << qC;
        cout.flush();
        int ans1 = readAnswerOrExit();

        int W = -1;

        if (ans1 == 0) {
            // W in [1, C-1]
            cout << q1;
            cout.flush();
            int ans2 = readAnswerOrExit();
            for (int w = 1; w <= C - 1; ++w) {
                int lines = (N + w - 1) / w;
                if (lines == ans2) { W = w; break; }
            }
        } else {
            // Determine t = floor(W/C) from ans1 = ceil(N / t)
            int tt = -1;
            for (int cand = 1; cand <= 100000 / C; ++cand) {
                int lines = (N + cand - 1) / cand;
                if (lines == ans1) { tt = cand; break; }
            }
            if (tt == -1) exit(0);

            int L = C * tt;

            // Query 2: [L, 1, L, 2, L, ..., 316, L]
            string q2;
            q2.reserve(10 + 633 * 7);
            q2.push_back('?');
            q2.push_back(' ');
            appendInt(q2, 1 + 2 * M);
            q2.push_back(' ');
            appendInt(q2, L);
            for (int i = 1; i <= M; ++i) {
                q2.push_back(' ');
                appendInt(q2, i);
                q2.push_back(' ');
                appendInt(q2, L);
            }
            q2.push_back('\n');

            cout << q2;
            cout.flush();
            int ans2 = readAnswerOrExit();

            int r = 1 + 2 * M - ans2;
            W = L + r;
        }

        if (W < 1 || W > 100000) exit(0);

        cout << "! " << W << "\n";
        cout.flush();
    }

    return 0;
}