#include <bits/stdc++.h>
using namespace std;

static const int N_FIXED = 20;
static const int ALPH = 8;

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if(!(cin >> N >> M)) return 0;
    vector<string> s(M);
    for(int i=0;i<M;i++) cin >> s[i];

    vector<int> slen(M);
    for(int i=0;i<M;i++) slen[i] = (int)s[i].size();

    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto countCovered = [&](const vector<string>& grid)->int{
        int cnt = 0;
        for(int idx=0; idx<M; idx++){
            const string &t = s[idx];
            int k = slen[idx];
            bool ok = false;
            // horizontal
            for(int r=0;r<N;r++){
                for(int st=0;st<N;st++){
                    bool match = true;
                    for(int p=0;p<k;p++){
                        if(grid[r][(st+p)%N] != t[p]) { match = false; break; }
                    }
                    if(match){ ok = true; goto done; }
                }
            }
            // vertical
            for(int c=0;c<N;c++){
                for(int st=0;st<N;st++){
                    bool match = true;
                    for(int p=0;p<k;p++){
                        if(grid[(st+p)%N][c] != t[p]) { match = false; break; }
                    }
                    if(match){ ok = true; goto done; }
                }
            }
            done:
            if(ok) cnt++;
        }
        return cnt;
    };

    auto greedyBuild = [&](const vector<int>& order)->vector<string>{
        vector<string> grid(N, string(N, '.'));
        // process each string
        for(int odx=0; odx<(int)order.size(); odx++){
            int idx = order[odx];
            const string &t = s[idx];
            int k = slen[idx];

            int bestReuse = -1;
            int bestNew = INT_MAX;
            int bestDir = -1;
            int bestI = -1, bestJ = -1;
            int tieCount = 0;

            // dir 0: horizontal, dir 1: vertical
            // horizontal
            for(int r=0;r<N;r++){
                for(int st=0;st<N;st++){
                    int reuse = 0, newc = 0;
                    bool conflict = false;
                    for(int p=0;p<k;p++){
                        int rr = r;
                        int cc = (st + p) % N;
                        char ch = grid[rr][cc];
                        if(ch == '.') newc++;
                        else if(ch == t[p]) reuse++;
                        else { conflict = true; break; }
                    }
                    if(conflict) continue;
                    if(reuse > bestReuse || (reuse == bestReuse && newc < bestNew)){
                        bestReuse = reuse;
                        bestNew = newc;
                        bestDir = 0;
                        bestI = r;
                        bestJ = st;
                        tieCount = 1;
                    } else if(reuse == bestReuse && newc == bestNew){
                        ++tieCount;
                        if((int)(rng() % tieCount) == 0){
                            bestDir = 0;
                            bestI = r;
                            bestJ = st;
                        }
                    }
                }
            }
            // vertical
            for(int c=0;c<N;c++){
                for(int st=0;st<N;st++){
                    int reuse = 0, newc = 0;
                    bool conflict = false;
                    for(int p=0;p<k;p++){
                        int rr = (st + p) % N;
                        int cc = c;
                        char ch = grid[rr][cc];
                        if(ch == '.') newc++;
                        else if(ch == t[p]) reuse++;
                        else { conflict = true; break; }
                    }
                    if(conflict) continue;
                    if(reuse > bestReuse || (reuse == bestReuse && newc < bestNew)){
                        bestReuse = reuse;
                        bestNew = newc;
                        bestDir = 1;
                        bestI = c;
                        bestJ = st;
                        tieCount = 1;
                    } else if(reuse == bestReuse && newc == bestNew){
                        ++tieCount;
                        if((int)(rng() % tieCount) == 0){
                            bestDir = 1;
                            bestI = c;
                            bestJ = st;
                        }
                    }
                }
            }

            if(bestReuse >= 0){
                if(bestDir == 0){
                    int r = bestI, st = bestJ;
                    for(int p=0;p<k;p++){
                        int rr = r;
                        int cc = (st + p) % N;
                        grid[rr][cc] = t[p];
                    }
                }else if(bestDir == 1){
                    int c = bestI, st = bestJ;
                    for(int p=0;p<k;p++){
                        int rr = (st + p) % N;
                        int cc = c;
                        grid[rr][cc] = t[p];
                    }
                }
            }
        }
        // fill remaining with random letters
        for(int i=0;i<N;i++){
            for(int j=0;j<N;j++){
                if(grid[i][j]=='.'){
                    grid[i][j] = char('A' + (rng()%ALPH));
                }
            }
        }
        return grid;
    };

    // prepare orders
    vector<int> baseOrder(M);
    iota(baseOrder.begin(), baseOrder.end(), 0);
    stable_sort(baseOrder.begin(), baseOrder.end(), [&](int a, int b){
        if(slen[a] != slen[b]) return slen[a] > slen[b];
        return a < b;
    });

    auto start = chrono::high_resolution_clock::now();
    const double TIME_LIMIT = 1.95;

    int bestC = -1;
    vector<string> bestGrid(N, string(N, 'A'));

    int iter = 0;
    while(true){
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if(elapsed > TIME_LIMIT) break;

        vector<int> order = baseOrder;
        // shuffle slightly for diversification
        // full shuffle to explore diverse orders
        shuffle(order.begin(), order.end(), rng);
        // bias by length: partially sort top by length
        stable_sort(order.begin(), order.end(), [&](int a, int b){
            if(slen[a] != slen[b]) return slen[a] > slen[b];
            return rng() & 1;
        });

        vector<string> grid = greedyBuild(order);

        int c = countCovered(grid);
        if(c > bestC){
            bestC = c;
            bestGrid = grid;
        }
        iter++;
    }

    for(int i=0;i<N;i++){
        cout << bestGrid[i] << "\n";
    }
    return 0;
}