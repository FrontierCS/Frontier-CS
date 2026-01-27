#include <bits/stdc++.h>
using namespace std;

struct Timer {
    chrono::high_resolution_clock::time_point st;
    Timer() { reset(); }
    void reset() { st = chrono::high_resolution_clock::now(); }
    double elapsed() const {
        return chrono::duration<double>(chrono::high_resolution_clock::now() - st).count();
    }
};

static const int H = 30, W = 30, N = H*W, S = N*4;
int to_dir[8][4] = {
    {1,0,-1,-1},
    {3,-1,-1,0},
    {-1,-1,3,2},
    {-1,2,1,-1},
    {1,0,3,2},
    {3,2,1,0},
    {2,-1,0,-1},
    {-1,3,-1,1},
};
int di[4] = {0,-1,0,1};
int dj[4] = {-1,0,1,0};

inline int rot_type(int t, int r){
    r &= 3;
    if(t<=3) return (t + r) & 3;
    if(t==4) return (r&1)?5:4;
    if(t==5) return (r&1)?4:5;
    if(t==6) return (r&1)?7:6;
    return (r&1)?6:7; // t==7
}

inline int opp(int d){ return d^2; }

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    vector<int> base(N);
    for(int i=0;i<H;i++){
        string s; if(!(cin>>s)) return 0;
        for(int j=0;j<W;j++){
            base[i*W+j] = s[j]-'0';
        }
    }
    // Precompute mask and internal pairs for each tile type
    int open_mask[8]={0};
    vector<array<int,2>> pairs_list[8];
    for(int t=0;t<8;t++){
        int m=0;
        for(int d=0;d<4;d++){
            if(to_dir[t][d]!=-1) m |= (1<<d);
        }
        open_mask[t]=m;
        // derive internal connection pairs: for any d with to[t][d]=d2, that indicates entering from d leads to d2; but pair of open sides forms an undirected pair.
        // We'll collect unique pairs by ensuring d<to_dir[t][d].
        vector<array<int,2>> ps;
        for(int d=0;d<4;d++){
            int d2 = to_dir[t][d];
            if(d2!=-1 && d<d2){
                ps.push_back({d,d2});
            }
        }
        pairs_list[t]=ps;
    }

    mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());
    Timer timer;

    auto compute_score = [&](const vector<int>& cur_t)->int{
        static int next_state[S];
        // Build next mapping
        for(int i=0;i<H;i++){
            for(int j=0;j<W;j++){
                int idx = i*W+j;
                int t = cur_t[idx];
                for(int d=0;d<4;d++){
                    int sidx = (idx<<2)|d;
                    int d2 = to_dir[t][d];
                    if(d2==-1){
                        next_state[sidx] = -1;
                        continue;
                    }
                    int ni = i + di[d2];
                    int nj = j + dj[d2];
                    if(ni<0||ni>=H||nj<0||nj>=W){
                        next_state[sidx] = -1;
                        continue;
                    }
                    int nd = (d2+2)&3;
                    int nidx = ( (ni*W+nj)<<2 ) | nd;
                    next_state[sidx] = nidx;
                }
            }
        }
        // Detect cycles and compute top two lengths
        static unsigned char visited[S];
        static int vis_id[S];
        static int pos_in[S];
        static int stack_nodes[S];
        memset(visited, 0, sizeof(visited));
        int best1=0, best2=0;
        int cur_id = 1;
        for(int s0=0;s0<S;s0++){
            if(visited[s0]) continue;
            int cur = s0;
            int sp = 0;
            while(true){
                if(cur==-1){ // dead end
                    for(int k=0;k<sp;k++) visited[stack_nodes[k]]=1;
                    break;
                }
                if(visited[cur]){
                    for(int k=0;k<sp;k++) visited[stack_nodes[k]]=1;
                    break;
                }
                if(vis_id[cur]==cur_id){
                    int cycle_len = sp - pos_in[cur];
                    if(cycle_len > best1){
                        best2 = best1; best1 = cycle_len;
                    }else if(cycle_len > best2){
                        best2 = cycle_len;
                    }
                    for(int k=0;k<sp;k++) visited[stack_nodes[k]]=1;
                    break;
                }
                vis_id[cur]=cur_id;
                pos_in[cur]=sp;
                stack_nodes[sp++] = cur;
                cur = next_state[cur];
            }
            cur_id++;
        }
        return best1 * best2;
    };

    auto greedy_refine = [&](vector<int>& rot, vector<int>& cur_t, double time_limit_remain){
        // local matching with synergy
        const int wpair = 2;
        // initialize cur_t
        for(int idx=0;idx<N;idx++){
            cur_t[idx] = rot_type(base[idx], rot[idx]);
        }
        vector<int> order(N);
        iota(order.begin(), order.end(), 0);
        int pass = 0;
        while(true){
            if(timer.elapsed() > time_limit_remain) break;
            pass++;
            shuffle(order.begin(), order.end(), rng);
            int changes = 0;
            for(int id=0; id<N; id++){
                int idx = order[id];
                int i = idx / W, j = idx % W;
                int best_r = rot[idx];
                int best_sc = -1;
                for(int r=0;r<4;r++){
                    int t = rot_type(base[idx], r);
                    int m = open_mask[t];
                    int sc = 0;
                    // edge matches
                    for(int d=0; d<4; d++){
                        if(!(m & (1<<d))) continue;
                        int ni = i + di[d];
                        int nj = j + dj[d];
                        if(ni<0||ni>=H||nj<0||nj>=W) continue;
                        int nidx = ni*W+nj;
                        int nt = cur_t[nidx];
                        int nm = open_mask[nt];
                        if(nm & (1<<opp(d))) sc += 1;
                    }
                    // synergy for pairs
                    for(auto &p : pairs_list[t]){
                        int a = p[0], b = p[1];
                        int ni1 = i + di[a], nj1 = j + dj[a];
                        int ni2 = i + di[b], nj2 = j + dj[b];
                        bool ok1=false, ok2=false;
                        if(ni1>=0&&ni1<H&&nj1>=0&&nj1<W){
                            int nidx1 = ni1*W+nj1;
                            if(open_mask[cur_t[nidx1]] & (1<<opp(a))) ok1=true;
                        }
                        if(ni2>=0&&ni2<H&&nj2>=0&&nj2<W){
                            int nidx2 = ni2*W+nj2;
                            if(open_mask[cur_t[nidx2]] & (1<<opp(b))) ok2=true;
                        }
                        if(ok1 && ok2) sc += wpair;
                    }
                    if(sc > best_sc){
                        best_sc = sc;
                        best_r = r;
                    }
                }
                if(best_r != rot[idx]){
                    rot[idx] = best_r;
                    cur_t[idx] = rot_type(base[idx], best_r);
                    changes++;
                }
            }
            if(changes == 0 || pass >= 6) break;
        }
    };

    // Initial solution: zeros
    vector<int> best_rot(N, 0), cur_rot(N, 0), cur_t(N);
    greedy_refine(cur_rot, cur_t, 1e9);
    int best_score = compute_score(cur_t);
    best_rot = cur_rot;

    double TL = 1.9; // seconds
    // Random restarts with greedy refinement
    while(timer.elapsed() < TL * 0.8){
        for(int i=0;i<N;i++){
            cur_rot[i] = (int)(rng() & 3);
        }
        greedy_refine(cur_rot, cur_t, TL*0.82);
        int sc = compute_score(cur_t);
        if(sc > best_score){
            best_score = sc;
            best_rot = cur_rot;
        }
    }
    // Hill climbing on best
    cur_rot = best_rot;
    for(int i=0;i<N;i++) cur_t[i] = rot_type(base[i], cur_rot[i]);
    int cur_score = best_score;
    int iters = 0;
    while(timer.elapsed() < TL){
        iters++;
        int idx = (int)(rng()%N);
        int old_r = cur_rot[idx];
        int new_r = (int)(rng() & 3);
        if(new_r == old_r) continue;
        cur_rot[idx] = new_r;
        for(int i=0;i<N;i++) cur_t[i] = rot_type(base[i], cur_rot[i]);
        int sc = compute_score(cur_t);
        if(sc >= cur_score){
            cur_score = sc;
            if(sc > best_score){
                best_score = sc;
                best_rot = cur_rot;
            }
        }else{
            // revert
            cur_rot[idx] = old_r;
        }
    }

    // Output best
    string out;
    out.reserve(N);
    for(int i=0;i<N;i++){
        out.push_back(char('0' + (best_rot[i] & 3)));
    }
    cout << out << '\n';
    return 0;
}