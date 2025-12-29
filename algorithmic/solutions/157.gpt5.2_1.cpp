#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, sz;
    DSU(int n=0){ init(n); }
    void init(int n_) {
        n = n_;
        p.resize(n);
        sz.assign(n, 1);
        iota(p.begin(), p.end(), 0);
    }
    int find(int x){
        while(p[x] != x){
            p[x] = p[p[x]];
            x = p[x];
        }
        return x;
    }
    bool unite(int a, int b){
        a = find(a); b = find(b);
        if(a == b) return false;
        if(sz[a] < sz[b]) swap(a,b);
        p[b] = a;
        sz[a] += sz[b];
        return true;
    }
};

struct Eval {
    int L = 0;        // largest tree size
    int sumTree = 0;  // sum of tree component sizes
    int matched = 0;  // matched edges total
    int bestEff = 0;  // best effective score among components
    long long score = 0;
};

static inline double now_sec() {
    using namespace std::chrono;
    static const auto st = steady_clock::now();
    return duration<double>(steady_clock::now() - st).count();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    int T;
    cin >> N >> T;
    vector<int> initBoard(N * N);
    int initEmpty = -1;
    for(int i = 0; i < N; i++){
        string s;
        cin >> s;
        for(int j = 0; j < N; j++){
            char c = s[j];
            int v = 0;
            if('0' <= c && c <= '9') v = c - '0';
            else v = c - 'a' + 10;
            initBoard[i * N + j] = v;
            if(v == 0) initEmpty = i * N + j;
        }
    }

    auto evaluate = [&](const vector<int>& b) -> Eval {
        Eval ev;
        DSU dsu(N * N);
        vector<pair<int,int>> edges;
        edges.reserve(2 * N * (N - 1));

        for(int i = 0; i < N; i++){
            for(int j = 0; j < N; j++){
                int id = i * N + j;
                int t = b[id];
                if(t == 0) continue;
                if(j + 1 < N){
                    int t2 = b[id + 1];
                    if(t2 != 0 && (t & 4) && (t2 & 1)) edges.emplace_back(id, id + 1);
                }
                if(i + 1 < N){
                    int t2 = b[id + N];
                    if(t2 != 0 && (t & 8) && (t2 & 2)) edges.emplace_back(id, id + N);
                }
            }
        }

        for(auto &e : edges) dsu.unite(e.first, e.second);

        vector<int> vcnt(N * N, 0), ecnt(N * N, 0);
        for(int id = 0; id < N * N; id++){
            if(b[id] == 0) continue;
            vcnt[dsu.find(id)]++;
        }
        for(auto &e : edges){
            int r = dsu.find(e.first);
            ecnt[r]++;
        }

        ev.matched = (int)edges.size();
        ev.bestEff = 0;
        ev.L = 0;
        ev.sumTree = 0;

        for(int r = 0; r < N * N; r++){
            int v = vcnt[r];
            if(v == 0) continue;
            int e = ecnt[r];
            if(e == v - 1){
                ev.L = max(ev.L, v);
                ev.sumTree += v;
            }
            int excess = max(0, e - (v - 1));
            int eff = v * 100 - excess * 80;
            ev.bestEff = max(ev.bestEff, eff);
        }

        ev.score = (long long)ev.L * 1000000000LL
                 + (long long)ev.bestEff * 1000000LL
                 + (long long)ev.sumTree * 1000LL
                 + (long long)ev.matched;
        return ev;
    };

    auto reverseMove = [&](char c) -> char {
        if(c == 'U') return 'D';
        if(c == 'D') return 'U';
        if(c == 'L') return 'R';
        return 'L';
    };

    auto legalMoves = [&](int empty) -> array<char,4> {
        array<char,4> mv = {'?', '?', '?', '?'};
        int cnt = 0;
        int r = empty / N, c = empty % N;
        if(r > 0) mv[cnt++] = 'U';
        if(r + 1 < N) mv[cnt++] = 'D';
        if(c > 0) mv[cnt++] = 'L';
        if(c + 1 < N) mv[cnt++] = 'R';
        for(; cnt < 4; cnt++) mv[cnt] = '?';
        return mv;
    };

    auto applyMove = [&](vector<int>& b, int& empty, char mv) {
        int ne = empty;
        if(mv == 'U') ne -= N;
        else if(mv == 'D') ne += N;
        else if(mv == 'L') ne -= 1;
        else if(mv == 'R') ne += 1;
        swap(b[empty], b[ne]);
        empty = ne;
    };

    const double TIME_LIMIT = 1.80;
    mt19937 rng((unsigned)chrono::high_resolution_clock::now().time_since_epoch().count());

    int maxTree = N * N - 1;

    Eval initEval = evaluate(initBoard);
    int globalBestS = initEval.L;
    int globalBestK = 0;
    string globalBestPath;

    int maxRestarts = 60;
    for(int r = 0; r < maxRestarts; r++){
        if(now_sec() > TIME_LIMIT) break;

        vector<int> b = initBoard;
        int empty = initEmpty;
        string path;
        path.reserve(T);

        Eval cur = initEval;
        int bestS = cur.L, bestK = 0;
        string bestPath;

        char lastMove = 0;

        double epsBase = 0.18 + 0.10 * (r % 3 == 0) + 0.06 * (r % 5 == 0);
        epsBase = min(0.35, epsBase);

        for(int step = 0; step < T; step++){
            if(now_sec() > TIME_LIMIT) break;

            auto mvs = legalMoves(empty);
            vector<char> moves;
            for(char c : mvs) if(c != '?') moves.push_back(c);

            // Evaluate candidates
            struct Cand { char mv; Eval ev; };
            vector<Cand> cands;
            cands.reserve(moves.size());

            int oldEmpty = empty;
            for(char mv : moves){
                applyMove(b, empty, mv);
                Eval ev = evaluate(b);
                applyMove(b, empty, reverseMove(mv)); // undo
                cands.push_back({mv, ev});
            }
            empty = oldEmpty;

            // Choose move
            double eps = epsBase * (1.0 - (double)step / (double)T) + 0.02;
            uniform_real_distribution<double> uni01(0.0, 1.0);

            char chosen = moves[0];
            Eval chosenEv = cands[0].ev;

            auto pickRandom = [&]() {
                vector<char> candMoves = moves;
                if(lastMove && candMoves.size() >= 2){
                    char rev = reverseMove(lastMove);
                    vector<char> filtered;
                    for(char mv : candMoves) if(mv != rev) filtered.push_back(mv);
                    if(!filtered.empty()) candMoves.swap(filtered);
                }
                uniform_int_distribution<int> uid(0, (int)candMoves.size() - 1);
                return candMoves[uid(rng)];
            };

            if(uni01(rng) < eps){
                chosen = pickRandom();
                for(auto &c : cands) if(c.mv == chosen) { chosenEv = c.ev; break; }
            } else {
                long long bestScore = LLONG_MIN;
                vector<int> bestIdx;
                for(int i = 0; i < (int)cands.size(); i++){
                    long long sc = cands[i].ev.score;
                    if(sc > bestScore){
                        bestScore = sc;
                        bestIdx.clear();
                        bestIdx.push_back(i);
                    } else if(sc == bestScore){
                        bestIdx.push_back(i);
                    }
                }
                uniform_int_distribution<int> uid(0, (int)bestIdx.size() - 1);
                int idx = bestIdx[uid(rng)];
                chosen = cands[idx].mv;
                chosenEv = cands[idx].ev;
            }

            // Apply chosen
            applyMove(b, empty, chosen);
            path.push_back(chosen);
            lastMove = chosen;
            cur = chosenEv;

            // Update best for this restart
            int k = (int)path.size();
            if(cur.L > bestS || (cur.L == bestS && (cur.L == maxTree) && k < bestK) || (cur.L == bestS && bestK == 0 && k < bestK)){
                bestS = cur.L;
                bestK = k;
                bestPath = path;
            }
            if(bestS == maxTree && bestK == 0){
                bestK = k;
                bestPath = path;
            }
            // Early exit if perfect and short enough
            if(cur.L == maxTree && k <= N * N) {
                // still keep going a bit if time, but often enough
            }
        }

        // Compare to global best
        if(bestS > globalBestS || (bestS == globalBestS && (bestS == maxTree ? bestK < globalBestK : bestK < globalBestK))) {
            globalBestS = bestS;
            globalBestK = bestK;
            globalBestPath = bestPath;
        }
        // In case no improvement but found perfect with shorter K than current perfect
        if(bestS == maxTree && globalBestS == maxTree && bestK < globalBestK){
            globalBestK = bestK;
            globalBestPath = bestPath;
        }
        if(globalBestS == maxTree && globalBestK == 0){
            globalBestK = (int)globalBestPath.size();
        }
    }

    // If bestK not set properly (e.g., never updated), keep 0.
    if(globalBestS == maxTree && globalBestK == 0) globalBestK = (int)globalBestPath.size();
    if(globalBestK > (int)globalBestPath.size()) globalBestK = (int)globalBestPath.size();

    cout << globalBestPath.substr(0, globalBestK) << "\n";
    return 0;
}