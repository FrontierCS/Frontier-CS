#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 16;
    int idx = 0, size = 0;
    char buf[BUFSIZE];

    inline char readChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template <class T>
    bool readInt(T &out) {
        char c;
        do {
            c = readChar();
            if (!c) return false;
        } while (c <= ' ');

        bool neg = false;
        if (c == '-') {
            neg = true;
            c = readChar();
        }

        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = readChar();
        }
        out = neg ? -val : val;
        return true;
    }
};

static inline void appendInt(string &s, int x) {
    char tmp[16];
    int len = 0;
    if (x == 0) tmp[len++] = '0';
    while (x > 0) {
        tmp[len++] = char('0' + (x % 10));
        x /= 10;
    }
    while (len--) s.push_back(tmp[len]);
}

static inline string toStringInt128(__int128 x) {
    if (x == 0) return "0";
    bool neg = false;
    if (x < 0) { neg = true; x = -x; }
    string s;
    while (x > 0) {
        int digit = (int)(x % 10);
        s.push_back(char('0' + digit));
        x /= 10;
    }
    if (neg) s.push_back('-');
    reverse(s.begin(), s.end());
    return s;
}

// Number of nodes at distance d from a node of depth t in a perfect binary tree of height H (root depth 0, leaves depth H).
static inline long long sphereCount(int H, int t, int d) {
    if (d == 0) return 1;
    if (d > H + t) return 0;

    long long ans = 0;

    // a = 0: go only downward within subtree
    if (d <= H - t) {
        ans += (1LL << d);
    }

    // a >= 1: go up a steps to ancestor w, then down b = d-a steps into the sibling subtree of the child on path to u
    int maxA = min(t, d - 1);
    for (int a = 1; a <= maxA; a++) {
        int b = d - a;
        // w depth = t-a; need b steps down from w within tree height: b <= H - (t-a)
        if (b <= H - (t - a)) {
            ans += (1LL << (b - 1));
        }
    }

    // a = d: ancestor itself (b=0)
    if (d <= t) ans += 1;

    return ans;
}

int main() {
    FastScanner fs;
    int h;
    if (!fs.readInt(h)) return 0;

    int H = h - 1;
    int n = (1 << h) - 1;
    int D = 2 * H;

    // Precompute counts cnt[depth][dist]
    vector<vector<long long>> cnt(h, vector<long long>(D + 1, 0));
    for (int t = 0; t <= H; t++) {
        for (int d = 0; d <= D; d++) {
            cnt[t][d] = sphereCount(H, t, d);
        }
    }

    // Query totals T[d] for d in [H..D]
    vector<__int128> T(D + 1, 0);
    const int B = 700; // safe chunk size to avoid pipe deadlocks

    for (int d = H; d <= D; d++) {
        __int128 sum = 0;
        for (int l = 1; l <= n; l += B) {
            int r = min(n, l + B - 1);

            string out;
            out.reserve((r - l + 1) * 16);
            for (int u = l; u <= r; u++) {
                out.push_back('?');
                out.push_back(' ');
                appendInt(out, u);
                out.push_back(' ');
                appendInt(out, d);
                out.push_back('\n');
            }
            fwrite(out.data(), 1, out.size(), stdout);
            fflush(stdout);

            for (int u = l; u <= r; u++) {
                long long ans;
                if (!fs.readInt(ans)) return 0;
                if (ans == -1) return 0;
                sum += (__int128)ans;
            }
        }
        T[d] = sum;
    }

    // Solve for W_t (sum of weights at depth t) using triangular system with distances d=H+t
    vector<__int128> W(h, 0);

    __int128 denomCommon = (__int128)1 << (H - 1); // valid for H>=1 (h>=2)
    for (int t = H; t >= 1; t--) {
        int d = H + t;
        __int128 res = T[d];
        for (int j = t + 1; j <= H; j++) {
            if (cnt[j][d] != 0) res -= W[j] * (__int128)cnt[j][d];
        }
        // For t>=1, cnt[t][H+t] == 2^(H-1)
        W[t] = res / denomCommon;
    }

    // Root depth 0 from d=H
    {
        int d = H;
        __int128 res = T[d];
        for (int j = 1; j <= H; j++) {
            if (cnt[j][d] != 0) res -= W[j] * (__int128)cnt[j][d];
        }
        __int128 denomRoot = (__int128)1 << H; // cnt[0][H] == 2^H
        W[0] = res / denomRoot;
    }

    __int128 S = 0;
    for (int t = 0; t <= H; t++) S += W[t];

    string ansStr = toStringInt128(S);
    string finalOut = "! " + ansStr + "\n";
    fwrite(finalOut.data(), 1, finalOut.size(), stdout);
    fflush(stdout);
    return 0;
}