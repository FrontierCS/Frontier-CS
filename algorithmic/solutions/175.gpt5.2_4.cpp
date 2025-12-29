#include <bits/stdc++.h>
using namespace std;

class FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    unsigned char buf[BUFSIZE];
    size_t idx = 0, size = 0;

    inline bool refill() {
        size = fread(buf, 1, BUFSIZE, stdin);
        idx = 0;
        return size != 0;
    }

public:
    inline bool readInt(int &out) {
        unsigned char c;
        do {
            if (idx >= size) {
                if (!refill()) return false;
            }
            c = buf[idx++];
        } while (c <= ' ');

        int sign = 1;
        if (c == '-') {
            sign = -1;
            if (idx >= size) {
                if (!refill()) return false;
            }
            c = buf[idx++];
        }
        int x = 0;
        while (c > ' ') {
            x = x * 10 + (c - '0');
            if (idx >= size) {
                if (!refill()) break;
            }
            c = buf[idx++];
        }
        out = x * sign;
        return true;
    }
};

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed) : x(seed) {}
    uint64_t next() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    uint64_t operator()() { return next(); }
};

struct Clause {
    int32_t a, b, c;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n, m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    vector<Clause> clauses;
    clauses.resize((size_t)m);

    for (int i = 0; i < m; i++) {
        int a, b, c;
        fs.readInt(a); fs.readInt(b); fs.readInt(c);
        clauses[i] = Clause{(int32_t)a, (int32_t)b, (int32_t)c};
    }

    if (n <= 0) {
        putchar('\n');
        return 0;
    }
    if (m == 0) {
        string out;
        out.reserve((size_t)n * 2 + 1);
        for (int i = 0; i < n; i++) {
            out.push_back('0');
            out.push_back(i + 1 == n ? '\n' : ' ');
        }
        fwrite(out.data(), 1, out.size(), stdout);
        return 0;
    }

    vector<int> occCnt(n, 0), posCnt(n, 0), negCnt(n, 0);
    for (int i = 0; i < m; i++) {
        int32_t lits[3] = {clauses[i].a, clauses[i].b, clauses[i].c};
        for (int k = 0; k < 3; k++) {
            int32_t lit = lits[k];
            int v = (int)abs(lit) - 1;
            occCnt[v]++;
            if (lit > 0) posCnt[v]++; else negCnt[v]++;
        }
    }

    vector<int> off(n + 1, 0);
    for (int i = 0; i < n; i++) off[i + 1] = off[i] + occCnt[i];
    int totalOcc = off[n];
    vector<uint32_t> occ((size_t)totalOcc);
    vector<int> cur = off;

    for (int i = 0; i < m; i++) {
        int32_t lits[3] = {clauses[i].a, clauses[i].b, clauses[i].c};
        for (int k = 0; k < 3; k++) {
            int32_t lit = lits[k];
            int v = (int)abs(lit) - 1;
            uint32_t sign = (lit < 0) ? 1u : 0u;
            uint32_t pack = (uint32_t(i) << 1) | sign;
            occ[(size_t)cur[v]++] = pack;
        }
    }

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)&seed;
    SplitMix64 rng(seed);

    vector<uint8_t> val(n, 0);
    for (int v = 0; v < n; v++) {
        uint8_t base = (posCnt[v] >= negCnt[v]) ? 1 : 0;
        if ((rng() % 10) == 0) base ^= 1; // 10% noise
        val[v] = base;
    }

    auto litSat = [&](int32_t lit) -> uint8_t {
        int v = (int)abs(lit) - 1;
        uint8_t sign = (lit < 0) ? 1 : 0;
        return (uint8_t)(val[v] ^ sign);
    };

    vector<uint8_t> satcnt((size_t)m);
    vector<int> pos((size_t)m, -1);
    vector<int> unsat;
    unsat.reserve((size_t)m / 8 + 1);
    int64_t satisfiedCount = m;

    for (int i = 0; i < m; i++) {
        uint8_t sc = (uint8_t)(litSat(clauses[i].a) + litSat(clauses[i].b) + litSat(clauses[i].c));
        satcnt[(size_t)i] = sc;
        if (sc == 0) {
            pos[(size_t)i] = (int)unsat.size();
            unsat.push_back(i);
            satisfiedCount--;
        }
    }

    auto addUnsat = [&](int cid) {
        int &p = pos[(size_t)cid];
        if (p != -1) return;
        p = (int)unsat.size();
        unsat.push_back(cid);
        satisfiedCount--;
    };

    auto removeUnsat = [&](int cid) {
        int &p = pos[(size_t)cid];
        if (p == -1) return;
        int idx = p;
        int last = unsat.back();
        unsat[idx] = last;
        pos[(size_t)last] = idx;
        unsat.pop_back();
        p = -1;
        satisfiedCount++;
    };

    vector<uint8_t> bestVal = val;
    int64_t bestSat = satisfiedCount;

    auto start = chrono::steady_clock::now();
    const double WALK_SECONDS = 1.0;
    int maxSteps = 5 * n;
    if (maxSteps < 2000) maxSteps = 2000;
    if (maxSteps > 30000) maxSteps = 30000;

    for (int step = 0; step < maxSteps && !unsat.empty(); step++) {
        if ((step & 63) == 0) {
            double elapsed = chrono::duration<double>(chrono::steady_clock::now() - start).count();
            if (elapsed > WALK_SECONDS) break;
        }

        int cid = unsat[(size_t)(rng() % unsat.size())];
        const Clause &cl = clauses[(size_t)cid];
        int pick = (int)(rng() % 3);
        int32_t lit = (pick == 0 ? cl.a : (pick == 1 ? cl.b : cl.c));
        int v = (int)abs(lit) - 1;

        uint8_t oldVal = val[v];
        val[v] ^= 1;

        for (int idx = off[v]; idx < off[v + 1]; idx++) {
            uint32_t pack = occ[(size_t)idx];
            int ocid = (int)(pack >> 1);
            uint32_t sign = pack & 1u;

            int oldSc = (int)satcnt[(size_t)ocid];
            int before = (int)(oldVal ^ (uint8_t)sign);
            int delta = before ? -1 : +1;
            int newSc = oldSc + delta;
            satcnt[(size_t)ocid] = (uint8_t)newSc;

            if (oldSc == 0 && newSc > 0) removeUnsat(ocid);
            else if (oldSc > 0 && newSc == 0) addUnsat(ocid);
        }

        if (satisfiedCount > bestSat) {
            bestSat = satisfiedCount;
            bestVal = val;
            if (bestSat == m) break;
        }
    }

    string out;
    out.reserve((size_t)n * 2 + 1);
    for (int i = 0; i < n; i++) {
        out.push_back(bestVal[i] ? '1' : '0');
        out.push_back(i + 1 == n ? '\n' : ' ');
    }
    fwrite(out.data(), 1, out.size(), stdout);
    return 0;
}