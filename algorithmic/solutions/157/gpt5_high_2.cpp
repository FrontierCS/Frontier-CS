#include <bits/stdc++.h>
using namespace std;

struct EvalRes {
    int S;      // largest tree size
    int E;      // total number of matching edges
    int LC;     // largest component size (by vertices)
};

struct Board {
    int N;
    vector<vector<int>> a;
    int ei, ej; // empty position

    Board(int n=0): N(n), a(n, vector<int>(n,0)), ei(0), ej(0) {}

    inline bool in(int i, int j) const {
        return (0 <= i && i < N && 0 <= j && j < N);
    }

    void applyMove(char mv) {
        // Move the adjacent tile into the empty square.
        int di=0, dj=0;
        if (mv=='U') { di=-1; dj=0; }
        else if (mv=='D') { di=1; dj=0; }
        else if (mv=='L') { di=0; dj=-1; }
        else if (mv=='R') { di=0; dj=1; }
        int ti = ei + di;
        int tj = ej + dj;
        // assume valid
        a[ei][ej] = a[ti][tj];
        a[ti][tj] = 0;
        ei = ti; ej = tj;
    }

    void undoMove(char mv) {
        // Inverse move
        if (mv=='U') applyMove('D');
        else if (mv=='D') applyMove('U');
        else if (mv=='L') applyMove('R');
        else if (mv=='R') applyMove('L');
    }

    static char inv(char c) {
        if (c=='U') return 'D';
        if (c=='D') return 'U';
        if (c=='L') return 'R';
        return 'L';
    }

    bool canMove(char mv) const {
        if (mv=='U') return (ei > 0);
        if (mv=='D') return (ei < N-1);
        if (mv=='L') return (ej > 0);
        if (mv=='R') return (ej < N-1);
        return false;
    }

    inline bool hasEdgeDir(int i, int j, int dir) const {
        // dir: 0=Up,1=Down,2=Left,3=Right
        // bits: Left=1, Up=2, Right=4, Down=8
        static const int di[4] = {-1, 1, 0, 0};
        static const int dj[4] = {0, 0, -1, 1};
        static const int bit[4] = {2, 8, 1, 4};
        static const int opp[4] = {1, 0, 3, 2};
        int ni = i + di[dir], nj = j + dj[dir];
        if (!in(ni, nj)) return false;
        int v = a[i][j], u = a[ni][nj];
        if (v==0 || u==0) return false;
        if ((v & bit[dir]) && (u & bit[opp[dir]])) return true;
        return false;
    }

    EvalRes evaluate() const {
        int N = this->N;
        vector<vector<char>> vis(N, vector<char>(N, 0));
        static const int di4[4] = {-1, 1, 0, 0};
        static const int dj4[4] = {0, 0, -1, 1};

        int bestTree = 0;
        int totalEdges = 0;
        int largestComp = 0;

        for (int i=0;i<N;i++) for (int j=0;j<N;j++) {
            if (a[i][j]==0 || vis[i][j]) continue;
            // BFS this component via existing edges
            queue<pair<int,int>> q;
            q.push({i,j}); vis[i][j]=1;
            int vcnt=0;
            int sumdeg=0;
            while(!q.empty()){
                auto [ci,cj]=q.front(); q.pop();
                vcnt++;
                int deg=0;
                for (int d=0; d<4; d++) {
                    if (hasEdgeDir(ci,cj,d)) {
                        deg++;
                        int ni=ci+di4[d], nj=cj+dj4[d];
                        if (!vis[ni][nj]) {
                            vis[ni][nj]=1;
                            q.push({ni,nj});
                        }
                    }
                }
                sumdeg += deg;
            }
            int ecomp = sumdeg/2;
            totalEdges += ecomp;
            largestComp = max(largestComp, vcnt);
            if (ecomp == vcnt - 1) {
                // It's a tree (connected and acyclic)
                bestTree = max(bestTree, vcnt);
            }
        }

        return {bestTree, totalEdges, largestComp};
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    long long T;
    if (!(cin >> N >> T)) {
        return 0;
    }
    vector<string> s(N);
    for (int i=0;i<N;i++) cin >> s[i];

    Board bd(N);
    for (int i=0;i<N;i++){
        for (int j=0;j<N;j++){
            char c = s[i][j];
            int v;
            if ('0'<=c && c<='9') v = c - '0';
            else v = 10 + (c - 'a');
            bd.a[i][j] = v;
            if (v==0) { bd.ei=i; bd.ej=j; }
        }
    }

    // Random engine
    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    mt19937_64 rng(seed);

    // Initial evaluation
    EvalRes evalBest = bd.evaluate();
    string ops;

    // We'll maintain the best prefix index to revert to best state at the end
    int best_idx = 0; // after ops[0..best_idx-1] applied
    // We choose moves while ensuring we can revert to best within T.
    auto canContinue = [&](int curLen, int bestIndex)->bool{
        long long needToRevert = curLen - bestIndex;
        // If we make another move now, we must ensure we can still revert later.
        // We allow another move if (curLen + 1) + ((curLen + 1) - bestIndex) <= T
        long long after = (curLen + 1) + (curLen + 1 - bestIndex);
        return (after <= T);
    };

    auto betterEval = [&](const EvalRes& A, const EvalRes& B)->int{
        // return 1 if A better, -1 if B better, 0 if equal
        if (A.S != B.S) return (A.S > B.S) ? 1 : -1;
        if (A.E != B.E) return (A.E > B.E) ? 1 : -1;
        if (A.LC != B.LC) return (A.LC > B.LC) ? 1 : -1;
        return 0;
    };

    auto getMoves = [&](const Board& b)->array<char,4>{
        array<char,4> cand = {'U','D','L','R'};
        return cand;
    };

    char lastMove = '?';

    // Exploration
    while ( (long long)ops.size() < T && canContinue((int)ops.size(), best_idx) ) {
        // Build candidate first moves (valid)
        vector<char> c1s;
        array<char,4> cand = {'U','D','L','R'};
        for (char c : cand) {
            if (bd.canMove(c)) c1s.push_back(c);
        }
        // Avoid immediate reverse if possible
        if (lastMove!='?' && !c1s.empty()) {
            char inv = Board::inv(lastMove);
            if (c1s.size() >= 2) {
                vector<char> filtered;
                for (char c : c1s) if (c != inv) filtered.push_back(c);
                if (!filtered.empty()) c1s.swap(filtered);
            }
        }
        if (c1s.empty()) break; // shouldn't happen

        // 2-step lookahead evaluation
        EvalRes chosenEval = {-1,-1,-1};
        char chosenC1 = c1s[0];
        vector<char> bestCands;

        for (char c1 : c1s) {
            bd.applyMove(c1);
            // generate c2s from here
            vector<char> c2s;
            for (char c2 : cand) {
                if (!bd.canMove(c2)) continue;
                if (c2 == Board::inv(c1)) continue; // avoid immediate revert in lookahead
                c2s.push_back(c2);
            }
            EvalRes bestAfterC1 = bd.evaluate(); // consider just after c1 as baseline
            // try c2s
            for (char c2 : c2s) {
                bd.applyMove(c2);
                EvalRes e2 = bd.evaluate();
                bd.undoMove(c2);
                if (betterEval(e2, bestAfterC1) > 0) {
                    bestAfterC1 = e2;
                }
            }
            bd.undoMove(c1);

            int cmp = betterEval(bestAfterC1, chosenEval);
            if (cmp > 0) {
                chosenEval = bestAfterC1;
                chosenC1 = c1;
                bestCands.clear();
                bestCands.push_back(c1);
            } else if (cmp == 0) {
                bestCands.push_back(c1);
            }
        }

        if (bestCands.size() > 1) {
            // Random tie-break
            chosenC1 = bestCands[rng() % bestCands.size()];
        }

        // Apply chosen move
        bd.applyMove(chosenC1);
        ops.push_back(chosenC1);
        lastMove = chosenC1;

        // Update best if improved
        EvalRes curEval = bd.evaluate();
        if (betterEval(curEval, evalBest) > 0) {
            evalBest = curEval;
            best_idx = (int)ops.size();
        }
    }

    // Revert to best state
    if ((int)ops.size() > best_idx) {
        string suf = ops.substr(best_idx);
        for (int k = (int)suf.size()-1; k >= 0; --k) {
            char mv = suf[k];
            char inv = Board::inv(mv);
            if ((long long)ops.size() < T) {
                ops.push_back(inv);
            } else {
                break;
            }
        }
    }

    // Ensure ops length <= T (it should)
    if ((long long)ops.size() > T) {
        ops.resize(T);
    }

    cout << ops << "\n";
    return 0;
}