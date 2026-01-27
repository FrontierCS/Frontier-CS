#include <bits/stdc++.h>
using namespace std;

struct XorShift64 {
    uint64_t x;
    XorShift64() {
        uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
        x = seed ^ 0x9e3779b97f4a7c15ULL;
        if (x == 0) x = 0x123456789abcdef0ULL;
    }
    inline uint64_t next() {
        x ^= x << 7;
        x ^= x >> 9;
        x ^= x << 8;
        return x;
    }
    inline uint32_t next3() {
        return (uint32_t)(next() % 3ULL);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int R, H;
    if (!(cin >> R >> H)) return 0;

    const int N = 1000;
    const int M = min(R, 64);
    XorShift64 rng;
    vector<uint64_t> code(N);

    const int maxAttempts = 20;
    bool ok = false;

    for (int attempt = 0; attempt < maxAttempts; ++attempt) {
        for (int i = 0; i < N; ++i) {
            uint64_t mask = 0;
            for (int b = 0; b < M; ++b) {
                if (rng.next3() == 0) mask |= (1ULL << b);
            }
            code[i] = mask;
        }

        size_t K = (size_t)N * (N + 1) / 2;
        vector<uint64_t> orvals;
        orvals.reserve(K);
        for (int i = 0; i < N; ++i) {
            for (int j = i; j < N; ++j) {
                orvals.emplace_back(code[i] | code[j]);
            }
        }
        sort(orvals.begin(), orvals.end());
        ok = true;
        for (size_t k = 1; k < orvals.size(); ++k) {
            if (orvals[k] == orvals[k - 1]) {
                ok = false;
                break;
            }
        }
        if (ok) break;
    }

    for (int b = 0; b < M; ++b) {
        vector<int> positions;
        positions.reserve(400);
        for (int i = 0; i < N; ++i) {
            if (code[i] & (1ULL << b)) positions.push_back(i + 1);
        }
        cout << "? " << positions.size();
        for (size_t k = 0; k < positions.size(); ++k) cout << ' ' << positions[k];
        cout << '\n' << flush;
    }

    cout << "@\n" << flush;

    int L;
    if (!(cin >> L)) return 0;
    vector<int> ans(L);
    for (int i = 0; i < L; ++i) cin >> ans[i];

    uint64_t y = 0;
    for (int i = 0; i < L && i < M; ++i) if (ans[i]) y |= (1ULL << i);

    int found_a = -1, found_b = -1;
    vector<int> cand;
    cand.reserve(N);
    for (int i = 0; i < N; ++i) {
        if ((code[i] & (~y)) == 0) cand.push_back(i);
    }

    for (size_t ii = 0; ii < cand.size(); ++ii) {
        int i = cand[ii];
        uint64_t mi = code[i];
        for (size_t jj = ii; jj < cand.size(); ++jj) {
            int j = cand[jj];
            if ((mi | code[j]) == y) {
                if (found_a == -1) {
                    found_a = i; found_b = j;
                }
            }
        }
    }

    if (found_a == -1) {
        for (int i = 0; i < N; ++i) {
            for (int j = i; j < N; ++j) {
                if ((code[i] | code[j]) == y) {
                    found_a = i; found_b = j;
                    break;
                }
            }
            if (found_a != -1) break;
        }
        if (found_a == -1) {
            found_a = 0; found_b = 0;
        }
    }

    cout << "! " << (found_a + 1) << ' ' << (found_b + 1) << '\n' << flush;
    return 0;
}