#include <bits/stdc++.h>
using namespace std;

static const int H = 8;
static const int W = 14;
static const int N = H*W;

int dr[8] = {-1,-1,-1,0,0,1,1,1};
int dc[8] = {-1,0,1,-1,1,-1,0,1};

int idx(int r,int c){return r*W+c;}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    // Precompute neighbors
    vector<array<int,8>> nbr(N);
    vector<int> deg(N,0);
    for(int r=0;r<H;r++){
        for(int c=0;c<W;c++){
            int u=idx(r,c);
            int d=0;
            for(int k=0;k<8;k++){
                int nr=r+dr[k], nc=c+dc[k];
                if(0<=nr && nr<H && 0<=nc && nc<W){
                    nbr[u][d++]=idx(nr,nc);
                }
            }
            deg[u]=d;
        }
    }

    auto now = []()->double{
        using namespace std::chrono;
        static auto st = high_resolution_clock::now();
        auto t = high_resolution_clock::now();
        return duration<double>(t-st).count();
    };

    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto can_read = [&](const array<uint8_t,N>& grid, const string& s)->bool{
        int L = (int)s.size();
        // Initialize active positions with first digit
        vector<int> cur;
        cur.reserve(N);
        int d0 = s[0]-'0';
        for(int u=0;u<N;u++) if(grid[u]==d0) cur.push_back(u);
        if(cur.empty()) return false;
        vector<char> mark(N,0), nextmark(N,0);
        for(int u:cur) mark[u]=1;

        for(int i=1;i<L;i++){
            int d = s[i]-'0';
            vector<int> nextlist;
            nextlist.reserve(N);
            // expand from current active positions
            for(int p:cur){
                for(int k=0;k<deg[p];k++){
                    int q = nbr[p][k];
                    if(grid[q]==d && !nextmark[q]){
                        nextmark[q]=1;
                        nextlist.push_back(q);
                    }
                }
            }
            if(nextlist.empty()) return false;
            // prepare for next iteration
            for(int u:cur) mark[u]=0;
            cur.swap(nextlist);
            for(int u:cur) nextmark[u]=0, mark[u]=1; // reset nextmark for next round and set mark for completeness (not strictly needed)
        }
        return !cur.empty();
    };

    auto score_grid = [&](const array<uint8_t,N>& grid, int soft_limit)->int{
        int k=1;
        string s;
        s.reserve(16);
        while(true){
            s = to_string(k);
            if(!can_read(grid, s)) return k-1;
            k++;
            if(soft_limit>0 && k>soft_limit) return soft_limit;
        }
    };

    // Initialize a random grid
    array<uint8_t,N> grid;
    for(int i=0;i<N;i++) grid[i] = rng()%10;

    // Slightly structured initialization: create some equal-digit adjacent pairs
    for(int r=0;r<H;r+=2){
        for(int c=0;c+1<W;c+=2){
            uint8_t d = rng()%10;
            grid[idx(r,c)] = d;
            if(c+1<W) grid[idx(r,c+1)] = d;
            if(r+1<H) grid[idx(r+1,c)] = d;
        }
    }
    // Random fill remaining
    for(int i=0;i<N;i++) if(rng()%5==0) grid[i]=rng()%10;

    int bestScore = score_grid(grid, 300);
    array<uint8_t,N> bestGrid = grid;

    double time_limit = 2.0; // seconds budget for search (well below 60s)
    int iter = 0;

    uniform_int_distribution<int> posDist(0, N-1);
    uniform_int_distribution<int> digDist(0, 9);
    uniform_int_distribution<int> mutCountDist(1, 3);

    while(now() < time_limit){
        array<uint8_t,N> cand = grid;
        int changes = mutCountDist(rng);
        array<int,3> changedPos{};
        array<uint8_t,3> oldVal{};
        for(int t=0;t<changes;t++){
            int p = posDist(rng);
            changedPos[t]=p;
            oldVal[t]=cand[p];
            uint8_t nv = digDist(rng);
            if(nv==cand[p]) nv = (nv+1)%10;
            cand[p]=nv;
        }

        // Progressive scoring with soft limits to prune slow evaluations
        int probe1 = max(50, bestScore - 20);
        int sc = score_grid(cand, probe1);
        if(sc >= probe1){
            int probe2 = bestScore + 50;
            sc = score_grid(cand, probe2);
            if(sc >= probe2){
                sc = score_grid(cand, 1000);
            }
        }

        // Accept if not worse with some probability, otherwise only if better
        if(sc > bestScore){
            bestScore = sc;
            bestGrid = cand;
            grid = cand;
        } else {
            // Small chance to accept sideways move to escape local minima
            if(sc == bestScore && (rng()%4==0)){
                grid = cand;
            } else if(rng()%100==0){
                grid = cand; // rare random jump
            }
        }
        iter++;
    }

    // If somehow bestGrid is weak, do a final refinement with a bit more targeted mutations
    // (short time, quick attempts)
    double extra_end = now() + 0.1;
    while(now() < extra_end){
        array<uint8_t,N> cand = bestGrid;
        for(int t=0;t<5;t++){
            int p = posDist(rng);
            cand[p]=digDist(rng);
        }
        int sc = score_grid(cand, bestScore + 50);
        if(sc > bestScore){
            bestScore = sc;
            bestGrid = cand;
        }
    }

    // Output best grid found
    for(int r=0;r<H;r++){
        for(int c=0;c<W;c++){
            cout << char('0' + bestGrid[idx(r,c)]);
        }
        cout << '\n';
    }
    return 0;
}