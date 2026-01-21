#include <bits/stdc++.h>
using namespace std;

struct DTNode {
    int pairId = -1;
    int left = -1, right = -1;
    int state = -1; // >=0 for leaf
};

static vector<array<int,5>> STATES;          // each: labels in increasing order
static vector<pair<int,int>> PAIRS;          // label pairs to compare
static vector<vector<uint8_t>> OUTCOME;      // OUTCOME[state][pairId] = 1 if label u < v
static vector<DTNode> DT;
static unordered_map<uint64_t, int> MEMO;    // key -> node index, -1 stored as 0xFFFFFFFF

static int buildDecisionTree(uint32_t mask, int depth) {
    if ((mask & (mask - 1)) == 0) {
        int st = __builtin_ctz(mask);
        DTNode node;
        node.state = st;
        DT.push_back(node);
        return (int)DT.size() - 1;
    }
    if (depth == 0) return -1;

    uint64_t key = (uint64_t(mask) << 3) | uint64_t(depth);
    auto it = MEMO.find(key);
    if (it != MEMO.end()) {
        uint32_t val = (uint32_t)it->second;
        if (val == 0xFFFFFFFFu) return -1;
        return (int)val;
    }

    // Choose a comparison that splits as evenly as possible
    int bestPair = -1;
    uint32_t bestL = 0, bestR = 0;
    int bestScore = -1;

    for (int pid = 0; pid < (int)PAIRS.size(); pid++) {
        uint32_t L = 0;
        for (int st = 0; st < (int)STATES.size(); st++) {
            if (mask & (1u << st)) {
                if (OUTCOME[st][pid]) L |= (1u << st);
            }
        }
        uint32_t R = mask & ~L;
        if (!L || !R) continue;
        int cL = __builtin_popcount(L);
        int cR = __builtin_popcount(R);
        int score = min(cL, cR);
        if (score > bestScore) {
            bestScore = score;
            bestPair = pid;
            bestL = L;
            bestR = R;
        }
    }

    // Try best-first, then all
    vector<int> orderPairs;
    if (bestPair != -1) orderPairs.push_back(bestPair);
    for (int pid = 0; pid < (int)PAIRS.size(); pid++) if (pid != bestPair) orderPairs.push_back(pid);

    for (int pid : orderPairs) {
        uint32_t L = 0;
        for (int st = 0; st < (int)STATES.size(); st++) {
            if (mask & (1u << st)) {
                if (OUTCOME[st][pid]) L |= (1u << st);
            }
        }
        uint32_t R = mask & ~L;
        if (!L || !R) continue;

        int left = buildDecisionTree(L, depth - 1);
        if (left == -1) continue;
        int right = buildDecisionTree(R, depth - 1);
        if (right == -1) continue;

        DTNode node;
        node.pairId = pid;
        node.left = left;
        node.right = right;
        DT.push_back(node);
        int id = (int)DT.size() - 1;
        MEMO[key] = (uint32_t)id;
        return id;
    }

    MEMO[key] = 0xFFFFFFFFu;
    return -1;
}

static void buildStatesAndTree() {
    // Labels: 0=A(top0), 1=B(top1), 2=P(i), 3=Q(i-1), 4=R(i-2), 5=C(old third, removed)
    const int A = 0, B = 1, P = 2, Q = 3, R = 4, C = 5;

    // Generate states via symbolic simulation of 3 insertions (types 0/1/2) into first 3.
    map<array<int,5>, int> uniq;
    for (int t1 = 0; t1 < 3; t1++) for (int t2 = 0; t2 < 3; t2++) for (int t3 = 0; t3 < 3; t3++) {
        vector<int> ord = {A, B, C}; // increasing order among all seen labels
        ord.insert(ord.begin() + t1, P);
        ord.insert(ord.begin() + t2, Q);
        ord.insert(ord.begin() + t3, R);

        array<int,5> s{};
        int k = 0;
        for (int x : ord) if (x != C) s[k++] = x;
        if (!uniq.count(s)) {
            int id = (int)STATES.size();
            uniq[s] = id;
            STATES.push_back(s);
        }
    }

    // Build list of pairs (comparisons). Skip (A,B) since known A<B always.
    for (int u = 0; u < 5; u++) {
        for (int v = u + 1; v < 5; v++) {
            if (u == A && v == B) continue;
            PAIRS.push_back({u, v});
        }
    }

    // Precompute outcomes.
    OUTCOME.assign(STATES.size(), vector<uint8_t>(PAIRS.size(), 0));
    for (int st = 0; st < (int)STATES.size(); st++) {
        int pos[5];
        for (int i = 0; i < 5; i++) pos[STATES[st][i]] = i;
        for (int pid = 0; pid < (int)PAIRS.size(); pid++) {
            auto [u, v] = PAIRS[pid];
            OUTCOME[st][pid] = (pos[u] < pos[v]) ? 1 : 0;
        }
    }

    DT.clear();
    MEMO.clear();

    uint32_t fullMask = 0;
    for (int i = 0; i < (int)STATES.size(); i++) fullMask |= (1u << i);

    int root = buildDecisionTree(fullMask, 5);
    // Root is stored at DT.back(); we will use its index.
    // Ensure it exists (should).
    if (root == -1) {
        // If something goes wrong, still leave DT empty; runtime will not proceed correctly.
        // But this should never happen.
    }
}

static int n;
static long long qcount = 0;
static long long qlimit = 0;

static bool ask(int i, int j) {
    // returns true iff a[i] < a[j]
    if (qcount >= qlimit) {
        // Avoid exceeding limit in case of bugs.
        exit(0);
    }
    cout << "? " << i << " " << j << "\n" << flush;
    char c;
    if (!(cin >> c)) exit(0);
    qcount++;
    return c == '<';
}

static array<int,3> sort3(int i, int j, int k) {
    int a = i, b = j, c = k;
    if (ask(b, a)) swap(a, b);
    if (ask(c, b)) swap(b, c);
    if (ask(b, a)) swap(a, b);
    return {a, b, c};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    buildStatesAndTree();

    if (!(cin >> n)) return 0;
    qlimit = (5LL * n) / 3 + 5;

    if (n == 1) {
        cout << "! 1\n" << flush;
        return 0;
    }
    if (n == 2) {
        vector<int> ord;
        if (ask(1, 2)) ord = {1, 2};
        else ord = {2, 1};
        vector<int> ans(n + 1);
        for (int r = 0; r < n; r++) ans[ord[r]] = r + 1;
        cout << "! " << ans[1] << " " << ans[2] << "\n" << flush;
        return 0;
    }

    // Initialize with last 3 indices.
    array<int,3> top = sort3(n - 2, n - 1, n); // top[0] < top[1] < top[2] by value
    deque<int> tail;

    auto insert1 = [&](int idxNew) {
        int a = top[0], b = top[1], c = top[2];
        // idxNew < c always by problem promise.
        if (ask(b, idxNew)) { // b < idxNew  => idxNew is third
            tail.push_front(c);
            top = {a, b, idxNew};
            return;
        }
        // idxNew < b
        if (ask(idxNew, a)) { // idxNew < a
            tail.push_front(c);
            top = {idxNew, a, b};
        } else { // a < idxNew < b
            tail.push_front(c);
            top = {a, idxNew, b};
        }
    };

    // Decision tree root index is the last node created for full mask.
    // Since buildDecisionTree creates nodes after children, root could be anywhere; we saved returned index in memo for full mask.
    // Recompute root via memo:
    uint32_t fullMask = 0;
    for (int i = 0; i < (int)STATES.size(); i++) fullMask |= (1u << i);
    uint64_t rootKey = (uint64_t(fullMask) << 3) | 5ull;
    int root = -1;
    auto it = MEMO.find(rootKey);
    if (it != MEMO.end() && (uint32_t)it->second != 0xFFFFFFFFu) root = (int)(uint32_t)it->second;
    if (root == -1) {
        // Should not happen; fallback to safe but query-heavy (may exceed limit).
        // We'll still proceed with single insertions.
        for (int i = n - 3; i >= 1; --i) insert1(i);
    } else {
        int cur = n - 3;
        while (cur >= 3) {
            int p = cur, q = cur - 1, r = cur - 2;
            int oldC = top[2];

            int idx[5];
            idx[0] = top[0]; // A
            idx[1] = top[1]; // B
            idx[2] = p;      // P
            idx[3] = q;      // Q
            idx[4] = r;      // R

            int node = root;
            while (DT[node].state == -1) {
                auto [u, v] = PAIRS[DT[node].pairId];
                bool uv = ask(idx[u], idx[v]);
                node = uv ? DT[node].left : DT[node].right;
            }
            int st = DT[node].state;
            const auto &ordLabels = STATES[st];

            int s0 = idx[ordLabels[0]];
            int s1 = idx[ordLabels[1]];
            int s2 = idx[ordLabels[2]];
            int s3 = idx[ordLabels[3]];
            int s4 = idx[ordLabels[4]];

            // Prepend [s3, s4, oldC] to tail (in increasing order).
            tail.push_front(oldC);
            tail.push_front(s4);
            tail.push_front(s3);

            top = {s0, s1, s2};

            cur -= 3;
        }
        // Remaining 0..2 indices: insert individually.
        for (int i = cur; i >= 1; --i) insert1(i);
    }

    vector<int> ord;
    ord.reserve(n);
    ord.push_back(top[0]);
    ord.push_back(top[1]);
    ord.push_back(top[2]);
    for (int x : tail) ord.push_back(x);

    vector<int> ans(n + 1);
    for (int rank = 1; rank <= n; rank++) ans[ord[rank - 1]] = rank;

    cout << "! ";
    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << ' ';
        cout << ans[i];
    }
    cout << "\n" << flush;
    return 0;
}