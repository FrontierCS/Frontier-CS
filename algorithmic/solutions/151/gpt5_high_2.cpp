#include <bits/stdc++.h>
using namespace std;

struct Dijkstra {
    int N;
    int TOT;
    const vector<int> *cost; // -1 for obstacle, 5..9 for road
    vector<int> dist;
    vector<int> prev;
    vector<char> dir;
    Dijkstra(int N_, const vector<int> *cost_): N(N_), TOT(N_*N_), cost(cost_) {
        dist.assign(TOT, INT_MAX);
        prev.assign(TOT, -1);
        dir.assign(TOT, 0);
    }
    inline bool inb(int i,int j){ return 0<=i && i<N && 0<=j && j<N; }
    void run(int s) {
        fill(dist.begin(), dist.end(), INT_MAX);
        fill(prev.begin(), prev.end(), -1);
        fill(dir.begin(), dir.end(), 0);
        struct Node { int d, v; };
        struct Cmp { bool operator()(const Node& a, const Node& b) const { return a.d > b.d; } };
        priority_queue<Node, vector<Node>, Cmp> pq;
        dist[s] = 0;
        pq.push({0, s});
        static const int di[4] = {-1,1,0,0};
        static const int dj[4] = {0,0,-1,1};
        static const char dc[4] = {'U','D','L','R'};
        while(!pq.empty()){
            Node cur = pq.top(); pq.pop();
            int d = cur.d, v = cur.v;
            if(d != dist[v]) continue;
            int i = v / N, j = v % N;
            for(int k=0;k<4;k++){
                int ni = i + di[k], nj = j + dj[k];
                if(!inb(ni,nj)) continue;
                int to = ni * N + nj;
                int w = (*cost)[to];
                if(w < 0) continue; // obstacle
                int nd = d + w;
                if(nd < dist[to]){
                    dist[to] = nd;
                    prev[to] = v;
                    dir[to] = dc[k];
                    pq.push({nd, to});
                }
            }
        }
    }
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, si, sj;
    if(!(cin >> N >> si >> sj)) {
        return 0;
    }
    vector<string> c(N);
    for(int i=0;i<N;i++) cin >> c[i];

    int TOT = N*N;
    vector<int> cost(TOT, -1);
    for(int i=0;i<N;i++){
        for(int j=0;j<N;j++){
            if(c[i][j] != '#') cost[i*N + j] = c[i][j]-'0';
        }
    }

    // Build run IDs for horizontal (even rows) and vertical (even cols)
    vector<vector<int>> runHId(N, vector<int>(N, -1));
    vector<vector<int>> runVId(N, vector<int>(N, -1));
    vector<vector<int>> runHCells; // list of cell ids per run
    vector<vector<int>> runVCells;

    // Horizontal runs on even rows
    for(int i=0;i<N;i++){
        if(i%2!=0) continue;
        int j=0;
        while(j<N){
            if(cost[i*N+j] < 0){ j++; continue; }
            int j0=j;
            while(j+1<N && cost[i*N+(j+1)] >= 0) j++;
            int j1=j;
            int L = j1 - j0 + 1;
            if(L >= 2){
                int id = (int)runHCells.size();
                runHCells.emplace_back();
                for(int jj=j0;jj<=j1;jj++){
                    runHId[i][jj] = id;
                    runHCells.back().push_back(i*N + jj);
                }
            }
            // else ignore length-1 segments
            j = j1 + 1;
        }
    }

    // Vertical runs on even cols
    for(int j=0;j<N;j++){
        if(j%2!=0) continue;
        int i=0;
        while(i<N){
            if(cost[i*N+j] < 0){ i++; continue; }
            int i0=i;
            while(i+1<N && cost[(i+1)*N + j] >= 0) i++;
            int i1=i;
            int L = i1 - i0 + 1;
            if(L >= 2){
                int id = (int)runVCells.size();
                runVCells.emplace_back();
                for(int ii=i0; ii<=i1; ii++){
                    runVId[ii][j] = id;
                    runVCells.back().push_back(ii*N + j);
                }
            }
            // else ignore length-1 segments
            i = i1 + 1;
        }
    }

    int Hcnt = (int)runHCells.size();
    int Vcnt = (int)runVCells.size();
    vector<char> coveredH(Hcnt, 0), coveredV(Vcnt, 0);

    // Initial coverage at start
    if(si%2==0){
        int idh = runHId[si][sj];
        if(idh >= 0) coveredH[idh] = 1;
    }
    if(sj%2==0){
        int idv = runVId[si][sj];
        if(idv >= 0) coveredV[idv] = 1;
    }

    // Prepare Dijkstra solver
    Dijkstra dij(N, &cost);

    int cur = si*N + sj;
    string answer;

    // Seen arrays for temporary counting (timestamp technique)
    vector<int> seenH(Hcnt, -1), seenV(Vcnt, -1);
    int stamp = 0;

    auto calc_new_covers = [&](int s, int t, const vector<int>& prev)->int{
        if(t < 0 || t >= TOT) return 0;
        if(dij.dist[t] == INT_MAX) return 0;
        stamp++;
        int cnt = 0;
        int v = t;
        while(v != s && v != -1){
            int i = v / N, j = v % N;
            int idh = runHId[i][j];
            if(idh >= 0 && !coveredH[idh] && seenH[idh] != stamp){
                seenH[idh] = stamp;
                cnt++;
            }
            int idv = runVId[i][j];
            if(idv >= 0 && !coveredV[idv] && seenV[idv] != stamp){
                seenV[idv] = stamp;
                cnt++;
            }
            v = prev[v];
        }
        return cnt;
    };

    auto append_path_and_cover = [&](int s, int t){
        // reconstruct path from s to t
        vector<char> steps;
        int v = t;
        while(v != s && v != -1){
            steps.push_back(dij.dir[v]);
            v = dij.prev[v];
        }
        reverse(steps.begin(), steps.end());
        int ci = s / N, cj = s % N;
        for(char ch : steps){
            if(ch == 'U') ci--;
            else if(ch == 'D') ci++;
            else if(ch == 'L') cj--;
            else if(ch == 'R') cj++;
            // update coverage at new cell
            if(ci%2==0){
                int idh = runHId[ci][cj];
                if(idh >= 0) coveredH[idh] = 1;
            }
            if(cj%2==0){
                int idv = runVId[ci][cj];
                if(idv >= 0) coveredV[idv] = 1;
            }
            answer.push_back(ch);
        }
        return ci*N + cj;
    };

    auto all_covered = [&]()->bool{
        for(char x: coveredH) if(!x) return false;
        for(char x: coveredV) if(!x) return false;
        return true;
    };

    // Greedy visiting with benefit heuristic
    while(!all_covered()){
        dij.run(cur);

        // find best target among uncovered runs
        int bestT = -1;
        double bestScore = 1e100;
        int bestDist = INT_MAX;

        // helper to evaluate a run candidate given a list of cells
        auto consider_run = [&](const vector<vector<int>>& cells, const vector<char>& covered){
            for(int rid = 0; rid < (int)cells.size(); rid++){
                if(covered[rid]) continue;
                int bestCell = -1;
                int bestD = INT_MAX;
                const auto &lst = cells[rid];
                for(int v : lst){
                    if(dij.dist[v] < bestD){
                        bestD = dij.dist[v];
                        bestCell = v;
                    }
                }
                if(bestCell == -1 || bestD == INT_MAX) continue;
                int gain = calc_new_covers(cur, bestCell, dij.prev);
                if(gain <= 0) continue;
                double score = (double)bestD / (double)gain;
                if(score < bestScore || (abs(score - bestScore) < 1e-9 && bestD < bestDist)){
                    bestScore = score;
                    bestDist = bestD;
                    bestT = bestCell;
                }
            }
        };

        consider_run(runHCells, coveredH);
        consider_run(runVCells, coveredV);

        if(bestT == -1){
            // fallback: choose absolutely nearest road cell that improves anything
            int nearestT = -1;
            int nearestD = INT_MAX;
            for(int v=0; v<TOT; v++){
                if(dij.dist[v] == INT_MAX) continue;
                int i = v / N, j = v % N;
                bool need = false;
                int idh = runHId[i][j];
                int idv = runVId[i][j];
                if(idh >= 0 && !coveredH[idh]) need = true;
                if(idv >= 0 && !coveredV[idv]) need = true;
                if(need && dij.dist[v] < nearestD){
                    nearestD = dij.dist[v];
                    nearestT = v;
                }
            }
            if(nearestT == -1){
                // No progress possible; break
                break;
            } else {
                bestT = nearestT;
            }
        }

        cur = append_path_and_cover(cur, bestT);
    }

    // Return to start
    int start = si*N + sj;
    if(cur != start){
        dij.run(cur);
        if(dij.dist[start] != INT_MAX){
            cur = append_path_and_cover(cur, start);
        } else {
            // If somehow unreachable (shouldn't happen), do nothing
        }
    }

    cout << answer << "\n";
    return 0;
}