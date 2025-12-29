#include <bits/stdc++.h>
using namespace std;

static inline int popcnt64(uint64_t x) { return __builtin_popcountll(x); }

struct Pattern {
    int fixedCount = 0;
    array<vector<uint64_t>, 4> mask;
    vector<uint64_t> all;
    vector<int> blocks; // indices where all[b] != 0
};

struct Mod {
    uint32_t b;
    uint64_t oldA, oldC, oldG, oldT, oldAll;
};

int n, m;
int B;
vector<Pattern> pats;

array<vector<uint64_t>, 4> curMask;
vector<uint64_t> curAll;

vector<vector<Mod>> changes;
vector<long double> pow4neg;

long double ansSum = 0.0L, ansComp = 0.0L;

static inline void kahanAdd(long double term) {
    long double y = term - ansComp;
    long double t = ansSum + y;
    ansComp = (t - ansSum) - y;
    ansSum = t;
}

static inline void rollbackLevel(int level) {
    auto &mods = changes[level];
    for (int i = (int)mods.size() - 1; i >= 0; --i) {
        const Mod &md = mods[i];
        uint32_t b = md.b;
        curMask[0][b] = md.oldA;
        curMask[1][b] = md.oldC;
        curMask[2][b] = md.oldG;
        curMask[3][b] = md.oldT;
        curAll[b] = md.oldAll;
    }
    mods.clear();
}

static inline bool applyPatternAtLevel(const Pattern &p, int level, int &fixedAdd) {
    auto &mods = changes[level];
    mods.clear();
    fixedAdd = 0;

    for (int bi : p.blocks) {
        uint32_t b = (uint32_t)bi;

        uint64_t oA = curMask[0][b], oC = curMask[1][b], oG = curMask[2][b], oT = curMask[3][b];
        uint64_t oAll = curAll[b];

        uint64_t pA = p.mask[0][b], pC = p.mask[1][b], pG = p.mask[2][b], pT = p.mask[3][b];
        uint64_t pAll = p.all[b];

        if ((pA & (oAll & ~oA)) || (pC & (oAll & ~oC)) || (pG & (oAll & ~oG)) || (pT & (oAll & ~oT))) {
            rollbackLevel(level);
            return false;
        }

        fixedAdd += popcnt64(pAll & ~oAll);

        uint64_t nA = oA | pA;
        uint64_t nC = oC | pC;
        uint64_t nG = oG | pG;
        uint64_t nT = oT | pT;
        uint64_t nAll = oAll | pAll;

        if (nA != oA || nC != oC || nG != oG || nT != oT || nAll != oAll) {
            mods.push_back(Mod{b, oA, oC, oG, oT, oAll});
            curMask[0][b] = nA;
            curMask[1][b] = nC;
            curMask[2][b] = nG;
            curMask[3][b] = nT;
            curAll[b] = nAll;
        }
    }
    return true;
}

static void dfs(int idx, bool anyChosen, int parity, int fixedCount) {
    if (idx == (int)pats.size()) {
        if (!anyChosen) return;
        long double term = (parity ? 1.0L : -1.0L) * pow4neg[fixedCount];
        kahanAdd(term);
        return;
    }

    dfs(idx + 1, anyChosen, parity, fixedCount);

    int add = 0;
    if (applyPatternAtLevel(pats[idx], idx, add)) {
        dfs(idx + 1, true, parity ^ 1, fixedCount + add);
        rollbackLevel(idx);
    }
}

static bool equalPattern(const Pattern &a, const Pattern &b) {
    if (a.fixedCount != b.fixedCount) return false;
    for (int l = 0; l < 4; ++l) {
        if (a.mask[l] != b.mask[l]) return false;
    }
    return true;
}

// p subsumes q if any string matching q also matches p (p is more general or equal)
// This holds iff for all letters L: p.mask[L] subset of q.mask[L].
static bool subsumes(const Pattern &p, const Pattern &q) {
    if (p.fixedCount > q.fixedCount) return false;
    for (int l = 0; l < 4; ++l) {
        const auto &pm = p.mask[l];
        const auto &qm = q.mask[l];
        for (int b : p.blocks) {
            if (pm[b] & ~qm[b]) return false;
        }
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n >> m;
    B = (n + 63) / 64;

    vector<Pattern> input;
    input.reserve(m);

    for (int i = 0; i < m; ++i) {
        string s;
        cin >> s;
        Pattern p;
        for (int l = 0; l < 4; ++l) p.mask[l].assign(B, 0);
        p.all.assign(B, 0);

        for (int j = 0; j < n; ++j) {
            char ch = s[j];
            int l = -1;
            if (ch == 'A') l = 0;
            else if (ch == 'C') l = 1;
            else if (ch == 'G') l = 2;
            else if (ch == 'T') l = 3;
            if (l == -1) continue; // '?'
            int b = j >> 6;
            int bit = j & 63;
            p.mask[l][b] |= (1ULL << bit);
        }

        p.blocks.clear();
        p.fixedCount = 0;
        for (int b = 0; b < B; ++b) {
            uint64_t all = p.mask[0][b] | p.mask[1][b] | p.mask[2][b] | p.mask[3][b];
            p.all[b] = all;
            if (all) p.blocks.push_back(b);
            p.fixedCount += popcnt64(all);
        }
        input.push_back(std::move(p));
    }

    // Deduplicate
    vector<Pattern> uniq;
    uniq.reserve(input.size());
    for (auto &p : input) {
        bool dup = false;
        for (auto &q : uniq) {
            if (equalPattern(p, q)) { dup = true; break; }
        }
        if (!dup) uniq.push_back(std::move(p));
    }

    // Sort by fixedCount ascending for subsumption elimination
    sort(uniq.begin(), uniq.end(), [](const Pattern &a, const Pattern &b) {
        if (a.fixedCount != b.fixedCount) return a.fixedCount < b.fixedCount;
        return a.blocks.size() < b.blocks.size();
    });

    vector<char> removed(uniq.size(), 0);
    for (size_t i = 0; i < uniq.size(); ++i) {
        if (removed[i]) continue;
        for (size_t j = i + 1; j < uniq.size(); ++j) {
            if (removed[j]) continue;
            if (subsumes(uniq[i], uniq[j])) removed[j] = 1;
        }
    }

    pats.clear();
    for (size_t i = 0; i < uniq.size(); ++i) {
        if (!removed[i]) pats.push_back(std::move(uniq[i]));
    }

    if (pats.empty()) {
        cout << setprecision(20) << 0.0L << "\n";
        return 0;
    }
    for (auto &p : pats) {
        if (p.fixedCount == 0) {
            cout << setprecision(20) << 1.0L << "\n";
            return 0;
        }
    }

    // Reorder for recursion (often helps pruning on conflicts)
    sort(pats.begin(), pats.end(), [](const Pattern &a, const Pattern &b) {
        if (a.fixedCount != b.fixedCount) return a.fixedCount > b.fixedCount;
        return a.blocks.size() > b.blocks.size();
    });

    pow4neg.assign(n + 1, 1.0L);
    for (int k = 1; k <= n; ++k) pow4neg[k] = pow4neg[k - 1] * 0.25L;

    for (int l = 0; l < 4; ++l) curMask[l].assign(B, 0);
    curAll.assign(B, 0);

    changes.assign(pats.size() + 1, {});
    size_t maxBlocks = 0;
    for (auto &p : pats) maxBlocks = max(maxBlocks, p.blocks.size());
    for (auto &v : changes) v.reserve(maxBlocks);

    dfs(0, false, 0, 0);

    long double res = ansSum;
    if (res < 0) res = 0;
    if (res > 1) res = 1;

    cout << setprecision(20) << res << "\n";
    return 0;
}