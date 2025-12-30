#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    x ^= (x >> 31);
    return x;
}

bool generate_good_codes(uint64_t seed, vector<uint64_t> &codes, int N, int Q) {
    uint64_t mask = (Q == 64) ? ~0ULL : ((1ULL << Q) - 1);
    for (int i = 1; i <= N; ++i) {
        uint64_t x = splitmix64(seed + (uint64_t)i * 0x9e3779b97f4a7c15ULL);
        codes[i] = x & mask;
    }

    const int capPow = 20;
    const size_t cap = 1u << capPow;
    static vector<uint64_t> table;
    static vector<unsigned char> used;
    table.assign(cap, 0);
    used.assign(cap, 0);

    auto add = [&](uint64_t v) -> bool {
        uint64_t h = (v * 11400714819323198485ULL) & (cap - 1);
        while (used[h]) {
            if (table[h] == v) return false; // duplicate pattern -> not injective
            h = (h + 1) & (cap - 1);
        }
        used[h] = 1;
        table[h] = v;
        return true;
    };

    for (int i = 1; i <= N; ++i) {
        for (int j = i; j <= N; ++j) {
            uint64_t v = codes[i] | codes[j];
            if (!add(v)) return false;
        }
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int R, H;
    if (!(cin >> R >> H)) return 0;

    const int N = 1000;
    const int Qdesired = 55;
    int Q = min(R, Qdesired); // R is expected to be 75, so Q=55
    if (Q <= 0) Q = 1;

    vector<uint64_t> codes(N + 1);
    uint64_t seed = 1;
    while (true) {
        if (generate_good_codes(seed, codes, N, Q)) break;
        ++seed;
    }

    // Send queries for each bit
    for (int bit = 0; bit < Q; ++bit) {
        vector<int> pos;
        pos.reserve(N);
        for (int i = 1; i <= N; ++i) {
            if ((codes[i] >> bit) & 1ULL) pos.push_back(i);
        }
        cout << "? " << pos.size();
        for (int x : pos) cout << ' ' << x;
        cout << '\n';
        cout.flush();
    }

    // Wait for answers
    cout << "@\n";
    cout.flush();

    int L;
    cin >> L;
    vector<int> res(L);
    for (int i = 0; i < L; ++i) cin >> res[i];

    int usedBits = min(Q, L);
    uint64_t ansMask = 0;
    for (int i = 0; i < usedBits; ++i) {
        if (res[i]) ansMask |= (1ULL << i);
    }

    int a = 1, b = 1;
    bool found = false;
    for (int i = 1; i <= N && !found; ++i) {
        for (int j = i; j <= N; ++j) {
            uint64_t v = codes[i] | codes[j];
            if ((v & ((usedBits == 64) ? ~0ULL : ((1ULL << usedBits) - 1))) == ansMask) {
                a = i;
                b = j;
                found = true;
                break;
            }
        }
    }

    cout << "! " << a << ' ' << b << '\n';
    cout.flush();

    return 0;
}