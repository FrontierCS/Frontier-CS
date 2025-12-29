#include <bits/stdc++.h>
using namespace std;

static int gN = 0;
static int gBlocks = 0;
static int gWords = 0;
static uint64_t gLastMask = ~0ULL;

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

struct Key {
    uint64_t h = 0;
    shared_ptr<uint64_t[]> data;

    Key() = default;
    Key(uint64_t hh, shared_ptr<uint64_t[]> dd) : h(hh), data(std::move(dd)) {}
};

struct KeyHash {
    size_t operator()(Key const& k) const noexcept {
        return (size_t)k.h;
    }
};

struct KeyEq {
    bool operator()(Key const& a, Key const& b) const noexcept {
        if (a.h != b.h) return false;
        const uint64_t* pa = a.data.get();
        const uint64_t* pb = b.data.get();
        for (int i = 0; i < gWords; i++) {
            if (pa[i] != pb[i]) return false;
        }
        return true;
    }
};

using I128 = __int128_t;

struct Item {
    I128 coeff = 0;
    int fixedCount = 0;
};

struct Update {
    Key key;
    I128 delta = 0;
    int fixedCount = 0;
};

static inline int letterCode(char c) {
    switch (c) {
        case 'A': return 0;
        case 'C': return 1;
        case 'G': return 2;
        case 'T': return 3;
    }
    return -1;
}

static Key makeKeyFromWords(const uint64_t* w) {
    auto arr = shared_ptr<uint64_t[]>(new uint64_t[gWords], default_delete<uint64_t[]>());
    uint64_t* p = arr.get();
    uint64_t h = 0x243f6a8885a308d3ULL;
    for (int i = 0; i < gWords; i++) {
        p[i] = w[i];
        h = splitmix64(h ^ p[i]);
    }
    return Key(h, std::move(arr));
}

static bool intersectKeyWithWords(const Key& A, const uint64_t* P, Key& out, int& fixedCount) {
    auto arr = shared_ptr<uint64_t[]>(new uint64_t[gWords], default_delete<uint64_t[]>());
    uint64_t* r = arr.get();

    const uint64_t* a = A.data.get();
    fixedCount = 0;
    uint64_t h = 0x13198a2e03707344ULL;

    for (int i = 0; i < gBlocks; i++) {
        uint64_t af = a[i];
        uint64_t pf = P[i];

        uint64_t al = a[gBlocks + i];
        uint64_t pl = P[gBlocks + i];

        uint64_t ah = a[2 * gBlocks + i];
        uint64_t ph = P[2 * gBlocks + i];

        uint64_t both = af & pf;
        uint64_t diff = ((al ^ pl) | (ah ^ ph)) & both;
        if (diff) return false;

        uint64_t rf = af | pf;
        uint64_t rl = (al & af) | (pl & pf);
        uint64_t rh = (ah & af) | (ph & pf);

        if (i == gBlocks - 1) {
            rf &= gLastMask;
            rl &= gLastMask;
            rh &= gLastMask;
        }

        r[i] = rf;
        r[gBlocks + i] = rl;
        r[2 * gBlocks + i] = rh;

        fixedCount += __builtin_popcountll(rf);

        h = splitmix64(h ^ rf);
        h = splitmix64(h ^ rl);
        h = splitmix64(h ^ rh);
    }

    out.h = h;
    out.data = std::move(arr);
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    gN = n;
    gBlocks = (n + 63) / 64;
    gWords = 3 * gBlocks;
    if (n % 64 == 0) gLastMask = ~0ULL;
    else gLastMask = (1ULL << (n % 64)) - 1ULL;

    vector<long double> powProb(n + 1);
    powProb[0] = 1.0L;
    for (int k = 1; k <= n; k++) {
        // exact power-of-two scaling until underflow in long double
        powProb[k] = ldexpl(1.0L, -2 * k);
    }

    unordered_map<Key, Item, KeyHash, KeyEq> mp;
    mp.reserve(1 << 14);

    string s;
    vector<uint64_t> pwords;
    pwords.resize(gWords);

    for (int pi = 0; pi < m; pi++) {
        cin >> s;

        fill(pwords.begin(), pwords.end(), 0ULL);
        uint64_t* pf = pwords.data();
        uint64_t* pl = pwords.data() + gBlocks;
        uint64_t* ph = pwords.data() + 2 * gBlocks;

        int fixedCount = 0;
        for (int pos = 0; pos < n; pos++) {
            char c = s[pos];
            if (c == '?') continue;
            int code = letterCode(c);
            int b = pos >> 6;
            int o = pos & 63;
            uint64_t bit = 1ULL << o;
            pf[b] |= bit;
            if (code & 1) pl[b] |= bit;
            if (code & 2) ph[b] |= bit;
        }
        if (gBlocks > 0) {
            pf[gBlocks - 1] &= gLastMask;
            pl[gBlocks - 1] &= gLastMask;
            ph[gBlocks - 1] &= gLastMask;
        }
        for (int i = 0; i < gBlocks; i++) fixedCount += __builtin_popcountll(pf[i]);

        vector<Update> updates;
        updates.reserve(mp.size() + 1);

        for (auto const& kv : mp) {
            const Key& k = kv.first;
            const Item& it = kv.second;
            Key inter;
            int interFixed = 0;
            if (intersectKeyWithWords(k, pwords.data(), inter, interFixed)) {
                updates.push_back(Update{std::move(inter), -it.coeff, interFixed});
            }
        }

        Key pkey = makeKeyFromWords(pwords.data());
        updates.push_back(Update{std::move(pkey), (I128)1, fixedCount});

        for (auto& up : updates) {
            if (up.delta == 0) continue;
            auto it = mp.find(up.key);
            if (it == mp.end()) {
                mp.emplace(std::move(up.key), Item{up.delta, up.fixedCount});
            } else {
                it->second.coeff += up.delta;
                if (it->second.coeff == 0) mp.erase(it);
            }
        }
    }

    long double sum = 0.0L, c = 0.0L;
    for (auto const& kv : mp) {
        const Item& it = kv.second;
        int fc = it.fixedCount;
        long double term = (long double)it.coeff * (fc <= n ? powProb[fc] : 0.0L);
        long double y = term - c;
        long double t = sum + y;
        c = (t - sum) - y;
        sum = t;
    }

    if (sum < 0 && sum > -1e-18L) sum = 0;
    if (sum > 1 && sum < 1 + 1e-18L) sum = 1;

    cout << setprecision(20) << (double)sum << "\n";
    return 0;
}