#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

static inline uint64_t hashVec(const vector<uint16_t>& v) {
    uint64_t h = 0x84222325cbf29ce4ULL ^ (uint64_t)v.size();
    for (uint16_t x : v) {
        h = splitmix64(h ^ (uint64_t)x);
    }
    return h;
}

enum Act { LEFT = 0, RIGHT = 1, STEP = 2 };

struct GreedyScore {
    int worstCells = INT_MAX;
    int worstStates = INT_MAX;
    bool ok = false;
};

struct Planner {
    int rc = 0;
    const vector<uint8_t>* dist = nullptr;
    const vector<int>* nextS = nullptr;

    struct Edge {
        int act = -1;
        vector<int> succ;
    };
    struct Node {
        vector<uint16_t> st;
        bool goal = false;
        vector<Edge> edges;
    };

    int maxNodes = 8000;

    int cellOf(uint16_t s) const { return (int)(s >> 2); }
    int dirOf(uint16_t s) const { return (int)(s & 3); }

    static inline uint16_t turnL(uint16_t s) {
        return (uint16_t)((s & ~3u) | ((s + 3u) & 3u));
    }
    static inline uint16_t turnR(uint16_t s) {
        return (uint16_t)((s & ~3u) | ((s + 1u) & 3u));
    }

    uint16_t trans(uint16_t s, int act) const {
        if (act == LEFT) return turnL(s);
        if (act == RIGHT) return turnR(s);
        // STEP
        int ns = (*nextS)[(int)s];
        return (uint16_t)ns;
    }

    bool isGoal(const vector<uint16_t>& b) const {
        if (b.empty()) return false;
        int c0 = cellOf(b[0]);
        for (uint16_t s : b) if (cellOf(s) != c0) return false;
        return true;
    }

    struct PlanRes {
        int status; // 0=FAIL, 1=ACTION, 2=NO
        int act;
    };

    PlanRes solve(const vector<uint16_t>& start, int maxNodesLimit) {
        maxNodes = maxNodesLimit;

        vector<Node> nodes;
        nodes.reserve(min(1024, maxNodes));

        unordered_map<uint64_t, vector<int>> mp;
        mp.reserve(2048);

        auto intern = [&](vector<uint16_t>&& v) -> int {
            uint64_t h = hashVec(v);
            auto& lst = mp[h];
            for (int id : lst) {
                if (nodes[id].st == v) return id;
            }
            int id = (int)nodes.size();
            Node nd;
            nd.st = std::move(v);
            nd.goal = isGoal(nd.st);
            nodes.push_back(std::move(nd));
            lst.push_back(id);
            return id;
        };

        vector<uint16_t> s0 = start;
        int startId = intern(std::move(s0));
        deque<int> q;
        q.push_back(startId);

        vector<char> inQueue;
        inQueue.reserve(maxNodes);

        // Build full reachable belief graph from start
        while (!q.empty()) {
            int u = q.front(); q.pop_front();

            // Generate edges from u
            Node &nu = nodes[u];
            if (!nu.edges.empty()) continue;

            bool stepSafe = true;
            for (uint16_t s : nu.st) {
                if ((*nextS)[(int)s] < 0) { stepSafe = false; break; }
            }

            array<int,3> acts = {LEFT, RIGHT, STEP};
            int actCount = stepSafe ? 3 : 2;

            nu.edges.reserve(actCount);

            for (int ai = 0; ai < actCount; ai++) {
                int act = acts[ai];

                // bucket by observation after action
                array<vector<uint16_t>, 100> buckets;
                vector<int> usedObs;
                usedObs.reserve(16);

                for (uint16_t s : nu.st) {
                    uint16_t s2 = trans(s, act);
                    uint8_t o = (*dist)[(int)s2];
                    if (buckets[o].empty()) usedObs.push_back((int)o);
                    buckets[o].push_back(s2);
                }

                Edge e;
                e.act = act;
                e.succ.reserve(usedObs.size());

                for (int o : usedObs) {
                    auto &bv = buckets[o];
                    sort(bv.begin(), bv.end());
                    int vid = intern(std::move(bv));
                    e.succ.push_back(vid);
                    if ((int)nodes.size() > maxNodes) {
                        return {0, -1}; // FAIL due to node limit
                    }
                }
                nu.edges.push_back(std::move(e));
            }

            // push newly created nodes to queue by scanning recent additions:
            // We don't have a direct record; so we push all nodes without edges.
            // Efficient enough for limited sizes: push any node added and not yet expanded by checking edges empty.
            for (int id = 0; id < (int)nodes.size(); id++) {
                if (nodes[id].edges.empty() && id != u) {
                    // to avoid repeated pushes, we can push anyway; edges check prevents re-expansion
                    q.push_back(id);
                }
            }
            // But above is O(V^2). Replace with a better method:
            // Not possible after-the-fact; thus use alternative: maintain q of nodes with empty edges at creation.
            // For now, keep within limits by leaving as-is? It can still be too slow.
            // We'll implement correct approach below by redoing build with explicit q at intern time.
            // (This code path won't be used; we'll return FAIL if it gets here.)
            return {0, -1};
        }

        return {0, -1};
    }

    PlanRes solve2(const vector<uint16_t>& start, int maxNodesLimit) {
        maxNodes = maxNodesLimit;

        vector<Node> nodes;
        nodes.reserve(min(2048, maxNodes));

        unordered_map<uint64_t, vector<int>> mp;
        mp.reserve(4096);

        deque<int> q;

        auto intern = [&](vector<uint16_t>&& v) -> int {
            uint64_t h = hashVec(v);
            auto& lst = mp[h];
            for (int id : lst) {
                if (nodes[id].st == v) return id;
            }
            int id = (int)nodes.size();
            Node nd;
            nd.st = std::move(v);
            nd.goal = isGoal(nd.st);
            nodes.push_back(std::move(nd));
            lst.push_back(id);
            q.push_back(id);
            return id;
        };

        vector<uint16_t> s0 = start;
        int startId = intern(std::move(s0));

        // Build reachable graph
        while (!q.empty()) {
            int u = q.front(); q.pop_front();
            Node &nu = nodes[u];
            if (!nu.edges.empty()) continue;

            bool stepSafe = true;
            for (uint16_t s : nu.st) {
                if ((*nextS)[(int)s] < 0) { stepSafe = false; break; }
            }

            array<int,3> acts = {LEFT, RIGHT, STEP};
            int actCount = stepSafe ? 3 : 2;

            nu.edges.reserve(actCount);

            for (int ai = 0; ai < actCount; ai++) {
                int act = acts[ai];

                array<vector<uint16_t>, 100> buckets;
                vector<int> usedObs;
                usedObs.reserve(16);

                for (uint16_t s : nu.st) {
                    uint16_t s2 = trans(s, act);
                    uint8_t o = (*dist)[(int)s2];
                    if (buckets[o].empty()) usedObs.push_back((int)o);
                    buckets[o].push_back(s2);
                }

                Edge e;
                e.act = act;
                e.succ.reserve(usedObs.size());

                for (int o : usedObs) {
                    auto &bv = buckets[o];
                    sort(bv.begin(), bv.end());
                    int vid = intern(std::move(bv));
                    e.succ.push_back(vid);
                    if ((int)nodes.size() > maxNodes) return {0, -1}; // FAIL
                }
                nu.edges.push_back(std::move(e));
            }
        }

        // Build predecessor lists
        vector<vector<pair<int,int>>> preds(nodes.size());
        preds.shrink_to_fit();
        for (int u = 0; u < (int)nodes.size(); u++) {
            for (int ei = 0; ei < (int)nodes[u].edges.size(); ei++) {
                for (int v : nodes[u].edges[ei].succ) {
                    preds[v].push_back({u, ei});
                }
            }
        }

        const int INF = 1e9;
        vector<int> distv(nodes.size(), INF);
        vector<int> bestEdge(nodes.size(), -1);
        vector<vector<int>> rem(nodes.size());
        vector<vector<int>> maxd(nodes.size());

        for (int u = 0; u < (int)nodes.size(); u++) {
            int m = (int)nodes[u].edges.size();
            rem[u].resize(m);
            maxd[u].assign(m, 0);
            for (int ei = 0; ei < m; ei++) rem[u][ei] = (int)nodes[u].edges[ei].succ.size();
        }

        using PII = pair<int,int>;
        priority_queue<PII, vector<PII>, greater<PII>> pq;
        for (int u = 0; u < (int)nodes.size(); u++) {
            if (nodes[u].goal) {
                distv[u] = 0;
                pq.push({0, u});
            }
        }

        while (!pq.empty()) {
            auto [du, v] = pq.top(); pq.pop();
            if (du != distv[v]) continue;

            for (auto [u, ei] : preds[v]) {
                if (rem[u][ei] <= 0) continue;
                rem[u][ei]--;
                if (du > maxd[u][ei]) maxd[u][ei] = du;
                if (rem[u][ei] == 0) {
                    int cand = 1 + maxd[u][ei];
                    if (cand < distv[u]) {
                        distv[u] = cand;
                        bestEdge[u] = ei;
                        pq.push({cand, u});
                    }
                }
            }
        }

        if (distv[startId] >= INF/2) return {2, -1}; // NO

        int ei = bestEdge[startId];
        if (ei < 0) {
            // start already goal, but main loop handles that. Still safe:
            return {1, LEFT};
        }
        return {1, nodes[startId].edges[ei].act};
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int r, c;
    if (!(cin >> r >> c)) return 0;
    vector<string> g(r);
    for (int i = 0; i < r; i++) cin >> g[i];
    int rc = r * c;

    auto inside = [&](int x, int y) { return 0 <= x && x < r && 0 <= y && y < c; };
    auto cellId = [&](int x, int y) { return x * c + y; };

    vector<char> isOpen(rc, 0);
    for (int i = 0; i < r; i++) for (int j = 0; j < c; j++) isOpen[cellId(i,j)] = (g[i][j] == '.');

    int S = rc * 4;
    vector<uint8_t> dist(S, 0);
    vector<int> nextS(S, -1);

    const int dx[4] = {-1, 0, 1, 0};
    const int dy[4] = {0, 1, 0, -1};

    for (int i = 0; i < r; i++) {
        for (int j = 0; j < c; j++) {
            int cell = cellId(i, j);
            if (!isOpen[cell]) continue;
            for (int dir = 0; dir < 4; dir++) {
                int sid = cell * 4 + dir;
                // step
                int ni = i + dx[dir], nj = j + dy[dir];
                if (inside(ni, nj) && isOpen[cellId(ni, nj)]) {
                    nextS[sid] = cellId(ni, nj) * 4 + dir;
                } else {
                    nextS[sid] = -1;
                }
                // dist
                int x = i, y = j;
                int d = 0;
                while (true) {
                    int nx = x + dx[dir], ny = y + dy[dir];
                    if (!inside(nx, ny) || !isOpen[cellId(nx, ny)]) break;
                    d++;
                    x = nx; y = ny;
                }
                dist[sid] = (uint8_t)d;
            }
        }
    }

    vector<uint16_t> belief;
    belief.reserve(S);
    for (int cell = 0; cell < rc; cell++) {
        if (!isOpen[cell]) continue;
        for (int dir = 0; dir < 4; dir++) belief.push_back((uint16_t)(cell * 4 + dir));
    }

    auto isGoal = [&](const vector<uint16_t>& b) -> bool {
        if (b.empty()) return false;
        int c0 = (int)(b[0] >> 2);
        for (uint16_t s : b) if (((int)s >> 2) != c0) return false;
        return true;
    };

    auto goalCell = [&](const vector<uint16_t>& b) -> int {
        return (int)(b[0] >> 2);
    };

    auto applyAction = [&](const vector<uint16_t>& b, int act) -> vector<uint16_t> {
        vector<uint16_t> out;
        out.reserve(b.size());
        if (act == LEFT) {
            for (uint16_t s : b) out.push_back((uint16_t)((s & ~3u) | ((s + 3u) & 3u)));
        } else if (act == RIGHT) {
            for (uint16_t s : b) out.push_back((uint16_t)((s & ~3u) | ((s + 1u) & 3u)));
        } else {
            for (uint16_t s : b) out.push_back((uint16_t)nextS[(int)s]);
        }
        sort(out.begin(), out.end());
        return out;
    };

    auto filterObs = [&](const vector<uint16_t>& b, int d) -> vector<uint16_t> {
        vector<uint16_t> out;
        out.reserve(b.size());
        for (uint16_t s : b) if ((int)dist[(int)s] == d) out.push_back(s);
        return out;
    };

    auto countUniqueCells = [&](const vector<uint16_t>& b) -> int {
        if (b.empty()) return 0;
        int cnt = 0;
        int last = -1;
        for (uint16_t s : b) {
            int cell = (int)(s >> 2);
            if (cell != last) {
                cnt++;
                last = cell;
            }
        }
        return cnt;
    };

    static vector<int> lastSeen; // size OBS*rc
    lastSeen.assign(100 * rc, 0);
    int stampCounter = 0;

    auto evalGreedy = [&](const vector<uint16_t>& b, int act) -> GreedyScore {
        GreedyScore gs;
        gs.ok = false;
        if (act == STEP) {
            for (uint16_t s : b) {
                if (nextS[(int)s] < 0) return gs;
            }
        }
        gs.ok = true;

        array<int, 100> cntStates{};
        array<int, 100> cntCells{};
        cntStates.fill(0);
        cntCells.fill(0);

        int stamp = ++stampCounter;
        for (uint16_t s : b) {
            int s2;
            if (act == LEFT) s2 = (int)((s & ~3u) | ((s + 3u) & 3u));
            else if (act == RIGHT) s2 = (int)((s & ~3u) | ((s + 1u) & 3u));
            else s2 = nextS[(int)s];

            int o = (int)dist[s2];
            cntStates[o]++;
            int cell = s2 >> 2;
            int idx = o * rc + cell;
            if (lastSeen[idx] != stamp) {
                lastSeen[idx] = stamp;
                cntCells[o]++;
            }
        }

        int worstC = 0, worstS = 0;
        for (int o = 0; o < 100; o++) {
            if (cntStates[o] > 0) {
                worstC = max(worstC, cntCells[o]);
                worstS = max(worstS, cntStates[o]);
            }
        }
        gs.worstCells = worstC;
        gs.worstStates = worstS;
        return gs;
    };

    unordered_map<uint64_t, int> beliefNextChoice;
    beliefNextChoice.reserve(4096);

    auto chooseGreedy = [&](const vector<uint16_t>& b) -> int {
        vector<pair<GreedyScore, int>> options;
        options.reserve(3);

        for (int act : {LEFT, RIGHT, STEP}) {
            GreedyScore sc = evalGreedy(b, act);
            if (!sc.ok) continue;
            options.push_back({sc, act});
        }
        if (options.empty()) return LEFT;

        sort(options.begin(), options.end(), [&](const auto& A, const auto& B) {
            const auto &a = A.first, &bsc = B.first;
            if (a.worstCells != bsc.worstCells) return a.worstCells < bsc.worstCells;
            if (a.worstStates != bsc.worstStates) return a.worstStates < bsc.worstStates;
            // prefer STEP if tie
            if (A.second != B.second) return A.second == STEP;
            return A.second < B.second;
        });

        uint64_t h = hashVec(b);
        int &idx = beliefNextChoice[h];
        int chosen = options[idx % (int)options.size()].second;
        idx++;
        return chosen;
    };

    auto actToStr = [&](int act) -> string {
        if (act == LEFT) return "left";
        if (act == RIGHT) return "right";
        return "step";
    };

    Planner planner;
    planner.rc = rc;
    planner.dist = &dist;
    planner.nextS = &nextS;

    int d;
    int rounds = 0;
    const int MAX_ROUNDS = 20000;

    while (cin >> d) {
        if (d == -1) return 0;

        belief = filterObs(belief, d);
        if (belief.empty()) {
            cout << "no\n" << flush;
            return 0;
        }
        if (isGoal(belief)) {
            int cell = goalCell(belief);
            int i = cell / c + 1;
            int j = cell % c + 1;
            cout << "yes " << i << " " << j << "\n" << flush;
            return 0;
        }

        int act = -1;

        int cellCnt = countUniqueCells(belief);
        if ((int)belief.size() <= 800 && cellCnt <= 300) {
            auto pr = planner.solve2(belief, 9000);
            if (pr.status == 2) {
                cout << "no\n" << flush;
                return 0;
            } else if (pr.status == 1) {
                act = pr.act;
            } else {
                act = chooseGreedy(belief);
            }
        } else {
            act = chooseGreedy(belief);
        }

        cout << actToStr(act) << "\n" << flush;

        belief = applyAction(belief, act);

        rounds++;
        if (rounds >= MAX_ROUNDS) {
            cout << "no\n" << flush;
            return 0;
        }
    }

    return 0;
}