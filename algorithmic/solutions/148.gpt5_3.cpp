#include <bits/stdc++.h>
using namespace std;

struct Xor64 {
    uint64_t x;
    Xor64(uint64_t seed=88172645463393265ull){ x = seed; }
    inline uint64_t next() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    inline int next_int(int a, int b){ // [a, b)
        return (int)(next() % (uint64_t)(b - a)) + a;
    }
    inline double next_double(){ // [0,1)
        return (next() >> 11) * (1.0/9007199254740992.0);
    }
};

struct Timer {
    chrono::steady_clock::time_point st;
    Timer() { reset(); }
    void reset() { st = chrono::steady_clock::now(); }
    double elapsed_ms() const {
        return chrono::duration_cast<chrono::milliseconds>(chrono::steady_clock::now() - st).count();
    }
    double elapsed_sec() const { return elapsed_ms() / 1000.0; }
};

static const int H = 50;
static const int W = 50;
static const int N = H*W;

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int si, sj;
    if(!(cin>>si>>sj)) return 0;
    vector<int> tile(N), val(N);
    int mx = -1;
    for(int i=0;i<H;i++){
        for(int j=0;j<W;j++){
            int x; cin>>x;
            tile[i*W+j] = x;
            if(x>mx) mx = x;
        }
    }
    for(int i=0;i<H;i++){
        for(int j=0;j<W;j++){
            int x; cin>>x;
            val[i*W+j] = x;
        }
    }
    int M = mx + 1;
    // adjacency only across different tiles
    vector<array<int,4>> neigh(N);
    vector<int> deg(N,0);
    for(int i=0;i<H;i++){
        for(int j=0;j<W;j++){
            int id = i*W+j;
            int d = 0;
            // U
            if(i-1>=0){
                int nid = (i-1)*W+j;
                if(tile[nid] != tile[id]) neigh[id][d++] = nid;
            }
            // D
            if(i+1<H){
                int nid = (i+1)*W+j;
                if(tile[nid] != tile[id]) neigh[id][d++] = nid;
            }
            // L
            if(j-1>=0){
                int nid = i*W+(j-1);
                if(tile[nid] != tile[id]) neigh[id][d++] = nid;
            }
            // R
            if(j+1<W){
                int nid = i*W+(j+1);
                if(tile[nid] != tile[id]) neigh[id][d++] = nid;
            }
            deg[id] = d;
            // fill remaining with -1
            for(int k=d;k<4;k++) neigh[id][k] = -1;
        }
    }

    auto dirChar = [&](int from, int to)->char{
        int fi = from / W, fj = from % W;
        int ti = to / W, tj = to % W;
        if(ti == fi-1 && tj == fj) return 'U';
        if(ti == fi+1 && tj == fj) return 'D';
        if(ti == fi && tj == fj-1) return 'L';
        if(ti == fi && tj == fj+1) return 'R';
        return 'U';
    };

    Timer timer;
    const double TIME_LIMIT_MS = 1900.0;

    Xor64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    string best_path;
    long long best_score = -1;

    // Heuristic parameters
    const double WEIGHT_SECOND = 0.65;
    const int K2 = 3;
    const double DEG_WEIGHT = 0.0;
    const double PENALTY_DEAD = 100.0;
    const double PENALTY_LEAF = 10.0;

    auto run_once = [&](uint64_t seed)->pair<string,long long>{
        Xor64 lrng(seed ^ rng.next());
        vector<char> used_tile(M, 0);
        int start = si*W+sj;
        used_tile[tile[start]] = 1;
        string path;
        long long score = val[start];
        int cur = start;

        int steps = 0;

        while(true){
            // Collect candidates
            struct Cand { int nb; double sc; };
            vector<Cand> cands;
            for(int k=0;k<deg[cur];k++){
                int nb = neigh[cur][k];
                if(nb<0) continue;
                int tnb = tile[nb];
                if(used_tile[tnb]) continue;

                // Evaluate nb
                // dedup for next-next step by tile id
                // gather values for each unique tile from adj[nb]
                int degRemUnique = 0;
                // We'll gather a tiny list of pairs (tileid, best_p)
                int buf_tid[8];
                int buf_val[8];
                int cc = 0;
                for(int kk=0; kk<deg[nb]; kk++){
                    int u = neigh[nb][kk];
                    if(u<0) continue;
                    int tu = tile[u];
                    if(used_tile[tu]) continue;
                    // dedup by tile
                    int pos = -1;
                    for(int q=0;q<cc;q++){
                        if(buf_tid[q]==tu){ pos = q; break; }
                    }
                    if(pos==-1){
                        buf_tid[cc] = tu;
                        buf_val[cc] = val[u];
                        cc++;
                    }else{
                        if(val[u] > buf_val[pos]) buf_val[pos] = val[u];
                    }
                }
                degRemUnique = cc;
                // sum of top K2
                if(cc>0){
                    // partial sort top K2
                    // since cc <= 4 typically, simple sort
                    for(int a=0;a<cc;a++){
                        for(int b=a+1;b<cc;b++){
                            if(buf_val[a] < buf_val[b]) swap(buf_val[a], buf_val[b]), swap(buf_tid[a], buf_tid[b]);
                        }
                    }
                }
                int take = min(K2, cc);
                int sum2 = 0;
                for(int a=0;a<take;a++) sum2 += buf_val[a];

                double sc = (double)val[nb] + WEIGHT_SECOND * (double)sum2 + DEG_WEIGHT * (double)degRemUnique;
                if(degRemUnique==0) sc -= PENALTY_DEAD;
                else if(degRemUnique==1) sc -= PENALTY_LEAF;

                sc += lrng.next_double() * 1e-7; // tiny noise
                cands.push_back({nb, sc});
            }

            if(cands.empty()) break;

            // sort candidates by score desc
            sort(cands.begin(), cands.end(), [](const Cand& a, const Cand& b){ return a.sc > b.sc; });

            // epsilon-greedy
            double eps;
            if(steps < 200) eps = 0.05;
            else if(steps < 800) eps = 0.03;
            else eps = 0.01;
            int pickIdx = 0;
            if(lrng.next_double() < eps){
                int topk = (int)min<size_t>(3, cands.size());
                pickIdx = lrng.next_int(0, topk);
            }
            int nb = cands[pickIdx].nb;

            // move
            path.push_back(dirChar(cur, nb));
            score += val[nb];
            used_tile[tile[nb]] = 1;
            cur = nb;
            steps++;

            if(timer.elapsed_ms() > TIME_LIMIT_MS) break;
        }

        return {path, score};
    };

    // Try multiple randomized runs within time limit
    while(timer.elapsed_ms() < TIME_LIMIT_MS){
        auto res = run_once(rng.next());
        if(res.second > best_score){
            best_score = res.second;
            best_path = mv(res.first);
        }
    }

    cout<<best_path<<"\n";
    return 0;
}