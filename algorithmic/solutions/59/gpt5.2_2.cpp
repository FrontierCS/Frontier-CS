#include <bits/stdc++.h>
using namespace std;

static int n;
static long long queryCount = 0;

static int cmpIdx(int i, int j) {
    // returns -1 if a_i < a_j, +1 if a_i > a_j
    cout << "? " << i << " " << j << '\n';
    cout.flush();
    char c;
    if (!(cin >> c)) exit(0);
    ++queryCount;
    if (c == '<') return -1;
    if (c == '>') return +1;
    exit(0);
}

struct Node {
    bool leaf = false;
    int i = -1, j = -1;
    int left = -1, right = -1;
    int pm = -1, pm1 = -1, pm2 = -1; // positions 0..4 for M, M-1, M-2
};

static vector<array<int,5>> configs;
static vector<int> posM, posM1, posM2;
static int outcome[60][5][5]; // 0: < , 1: >
static vector<Node> nodes;

static unordered_map<unsigned long long, int> memo;

static inline bool solved(uint64_t mask, int &tupleOut) {
    if (mask == 0) return false;
    int first = __builtin_ctzll(mask);
    int tuple = posM[first] + 5 * posM1[first] + 25 * posM2[first];
    uint64_t m = mask;
    while (m) {
        int c = __builtin_ctzll(m);
        int t = posM[c] + 5 * posM1[c] + 25 * posM2[c];
        if (t != tuple) return false;
        m &= (m - 1);
    }
    tupleOut = tuple;
    return true;
}

static int buildTree(uint64_t mask, int depth) {
    unsigned long long key = mask ^ (unsigned long long(depth) << 56);
    auto it = memo.find(key);
    if (it != memo.end()) return it->second;

    int tuple;
    if (solved(mask, tuple)) {
        Node nd;
        nd.leaf = true;
        nd.pm  = tuple % 5;
        nd.pm1 = (tuple / 5) % 5;
        nd.pm2 = (tuple / 25) % 5;
        nodes.push_back(nd);
        int idx = (int)nodes.size() - 1;
        memo[key] = idx;
        return idx;
    }

    if (depth == 0) {
        memo[key] = -1;
        return -1;
    }

    struct Candidate {
        int i, j;
        uint64_t L, R;
        int score;
    };
    vector<Candidate> cand;
    cand.reserve(10);

    for (int i = 0; i < 5; i++) for (int j = i + 1; j < 5; j++) {
        uint64_t L = 0, R = 0;
        uint64_t m = mask;
        while (m) {
            int c = __builtin_ctzll(m);
            m &= (m - 1);
            if (outcome[c][i][j] == 0) L |= (1ULL << c);
            else R |= (1ULL << c);
        }
        if (!L || !R) continue;
        int szL = __builtin_popcountll(L);
        int szR = __builtin_popcountll(R);
        int score = max(szL, szR);
        cand.push_back({i, j, L, R, score});
    }

    sort(cand.begin(), cand.end(), [](const Candidate& a, const Candidate& b){
        return a.score < b.score;
    });

    for (auto &c : cand) {
        int left = buildTree(c.L, depth - 1);
        if (left == -1) continue;
        int right = buildTree(c.R, depth - 1);
        if (right == -1) continue;

        Node nd;
        nd.leaf = false;
        nd.i = c.i; nd.j = c.j;
        nd.left = left; nd.right = right;
        nodes.push_back(nd);
        int idx = (int)nodes.size() - 1;
        memo[key] = idx;
        return idx;
    }

    memo[key] = -1;
    return -1;
}

static array<int,3> resolveLast5(int root, const array<int,5>& idx) {
    int cur = root;
    while (!nodes[cur].leaf) {
        int li = nodes[cur].i, lj = nodes[cur].j;
        int res = cmpIdx(idx[li], idx[lj]);
        cur = (res < 0) ? nodes[cur].left : nodes[cur].right;
    }
    return {nodes[cur].pm, nodes[cur].pm1, nodes[cur].pm2};
}

static void insertionSortSmall(vector<int>& v) {
    for (int i = 1; i < (int)v.size(); i++) {
        int x = v[i];
        int j = i;
        while (j > 0) {
            if (cmpIdx(x, v[j-1]) < 0) {
                v[j] = v[j-1];
                --j;
            } else break;
        }
        v[j] = x;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;
    if (!cin) return 0;

    // Build configurations: ranks 5(M),4(M-1),3(M-2),2(S1),1(S2)
    // Positions: 0..4 correspond to last5 in order.
    configs.clear();
    for (int pm = 2; pm <= 4; pm++) {
        for (int pm1 = 1; pm1 <= 4; pm1++) if (pm1 != pm) {
            for (int pm2 = 0; pm2 <= 4; pm2++) if (pm2 != pm && pm2 != pm1) {
                vector<int> rem;
                for (int p = 0; p < 5; p++) if (p != pm && p != pm1 && p != pm2) rem.push_back(p);
                // two small orders
                for (int t = 0; t < 2; t++) {
                    array<int,5> r{};
                    r.fill(0);
                    r[pm] = 5;
                    r[pm1] = 4;
                    r[pm2] = 3;
                    if (t == 0) { r[rem[0]] = 2; r[rem[1]] = 1; }
                    else { r[rem[0]] = 1; r[rem[1]] = 2; }
                    configs.push_back(r);
                }
            }
        }
    }

    int C = (int)configs.size(); // should be 54
    posM.assign(C, -1);
    posM1.assign(C, -1);
    posM2.assign(C, -1);
    for (int c = 0; c < C; c++) {
        for (int p = 0; p < 5; p++) {
            if (configs[c][p] == 5) posM[c] = p;
            else if (configs[c][p] == 4) posM1[c] = p;
            else if (configs[c][p] == 3) posM2[c] = p;
        }
        for (int i = 0; i < 5; i++) for (int j = i + 1; j < 5; j++) {
            outcome[c][i][j] = (configs[c][i] < configs[c][j]) ? 0 : 1;
        }
    }

    nodes.clear();
    memo.clear();
    memo.reserve(1 << 15);

    uint64_t fullMask = (C == 64) ? ~0ULL : ((1ULL << C) - 1ULL);
    int root = buildTree(fullMask, 5);
    if (root == -1) {
        // Should not happen; but avoid undefined behavior.
        return 0;
    }

    vector<int> L;
    L.reserve(n);
    for (int i = 1; i <= n; i++) L.push_back(i);

    vector<int> ans(n + 1, 0);

    while ((int)L.size() >= 5) {
        int m = (int)L.size();
        array<int,5> idx = { L[m-5], L[m-4], L[m-3], L[m-2], L[m-1] };
        auto p = resolveLast5(root, idx);
        int pm = p[0], pm1 = p[1], pm2 = p[2];

        ans[idx[pm]] = m;
        ans[idx[pm1]] = m - 1;
        ans[idx[pm2]] = m - 2;

        bool removed[5] = {false,false,false,false,false};
        removed[pm] = removed[pm1] = removed[pm2] = true;
        vector<int> keep;
        keep.reserve(2);
        for (int t = 0; t < 5; t++) if (!removed[t]) keep.push_back(idx[t]);

        L.resize(m - 5);
        L.push_back(keep[0]);
        L.push_back(keep[1]);
    }

    // Solve remaining with full sort by comparisons, then assign 1..m
    vector<int> rem = L;
    if (!rem.empty()) {
        insertionSortSmall(rem);
        for (int i = 0; i < (int)rem.size(); i++) ans[rem[i]] = i + 1;
    }

    cout << "!";
    for (int i = 1; i <= n; i++) cout << " " << ans[i];
    cout << '\n';
    cout.flush();
    return 0;
}