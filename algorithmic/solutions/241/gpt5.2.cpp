#include <bits/stdc++.h>
using namespace std;

struct Builder {
    string out;
    inline void ch(char c) { out.push_back(c); }
};

static int g_n;
static vector<int> g_mins;

static inline void buildAndMask(Builder &b, uint32_t mask) {
    if (mask == 0) { b.ch('T'); return; }
    if ((mask & (mask - 1)) == 0) {
        int idx = __builtin_ctz(mask);
        b.ch(char('a' + idx));
        return;
    }
    int cnt = __builtin_popcount(mask);
    int half = cnt / 2;
    uint32_t left = 0;
    uint32_t tmp = mask;
    for (int i = 0; i < half; i++) {
        uint32_t bit = tmp & (~tmp + 1u);
        left |= bit;
        tmp ^= bit;
    }
    uint32_t right = mask ^ left;
    b.ch('(');
    buildAndMask(b, left);
    b.ch('&');
    buildAndMask(b, right);
    b.ch(')');
}

static void buildOr(Builder &b, int l, int r) {
    if (r - l == 1) {
        buildAndMask(b, (uint32_t)g_mins[l]);
        return;
    }
    int m = (l + r) >> 1;
    b.ch('(');
    buildOr(b, l, m);
    b.ch('|');
    buildOr(b, m, r);
    b.ch(')');
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    cin >> T;
    while (T--) {
        int n;
        string s;
        cin >> n >> s;

        g_n = n;
        size_t L = 1ull << n;

        bool has0 = false, has1 = false;
        for (char c : s) {
            if (c == '0') has0 = true;
            else has1 = true;
        }

        if (!has1) {
            cout << "Yes\nF\n";
            continue;
        }
        if (!has0) {
            cout << "Yes\nT\n";
            continue;
        }

        bool mono = true;
        for (int i = 0; i < n && mono; i++) {
            int bit = 1 << i;
            for (int mask = 0; mask < (int)L; mask++) {
                if ((mask & bit) == 0) {
                    if (s[mask] == '1' && s[mask | bit] == '0') {
                        mono = false;
                        break;
                    }
                }
            }
        }

        if (!mono) {
            cout << "No\n";
            continue;
        }

        g_mins.clear();
        g_mins.reserve((int)L);
        long long leafCount = 0;
        for (int mask = 0; mask < (int)L; mask++) {
            if (s[mask] != '1') continue;
            bool minimal = true;
            int m = mask;
            while (m) {
                int bit = m & -m;
                int prev = mask ^ bit;
                if (s[prev] == '1') { minimal = false; break; }
                m ^= bit;
            }
            if (minimal) {
                g_mins.push_back(mask);
                leafCount += __builtin_popcount((unsigned)mask);
            }
        }

        if (g_mins.empty()) {
            cout << "Yes\nF\n";
            continue;
        }

        sort(g_mins.begin(), g_mins.end());

        Builder b;
        if (leafCount <= 0) leafCount = 1;
        b.out.reserve((size_t)min<long long>(max(32LL, 4 * leafCount + 16), 50'000'000LL));

        if ((int)g_mins.size() == 1) buildAndMask(b, (uint32_t)g_mins[0]);
        else buildOr(b, 0, (int)g_mins.size());

        cout << "Yes\n" << b.out << "\n";
    }
    return 0;
}