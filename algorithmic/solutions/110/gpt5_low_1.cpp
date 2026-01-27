#include <bits/stdc++.h>
using namespace std;

static const int H = 8;
static const int W = 14;
static const int N = H * W;

struct Grid {
    array<unsigned char, N> a; // digits 0..9
};

inline int idx(int r, int c){ return r*W + c; }

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    // Precompute neighbors (8-directional)
    vector<array<int,8>> nbr(N);
    vector<int> deg(N,0);
    for(int r=0;r<H;r++){
        for(int c=0;c<W;c++){
            int i = idx(r,c);
            int d=0;
            for(int dr=-1;dr<=1;dr++){
                for(int dc=-1;dc<=1;dc++){
                    if(dr==0 && dc==0) continue;
                    int nr=r+dr, nc=c+dc;
                    if(0<=nr && nr<H && 0<=nc && nc<W){
                        nbr[i][d++] = idx(nr,nc);
                    }
                }
            }
            deg[i]=d;
        }
    }

    auto now = [](){ return chrono::steady_clock::now(); };
    auto start = now();
    const double time_limit = 0.95; // seconds
    const double max_seconds = 0.95 * 60.0; // use most of 1 minute
    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    // DP buffers
    array<unsigned char, N> cur, nxt;

    auto readable = [&](const Grid &g, const string &s)->bool{
        int L = (int)s.size();
        // init cur: cells equal to first digit
        unsigned char d0 = (unsigned char)(s[0]-'0');
        for(int i=0;i<N;i++) cur[i] = (g.a[i]==d0);
        // progress
        for(int t=1;t<L;t++){
            unsigned char d = (unsigned char)(s[t]-'0');
            unsigned char any = 0;
            for(int i=0;i<N;i++){
                if(g.a[i]!=d){ nxt[i]=0; continue; }
                unsigned char ok = 0;
                int D = deg[i];
                for(int k=0;k<D;k++){
                    int j = nbr[i][k];
                    if(cur[j]){ ok=1; break; }
                }
                nxt[i]=ok;
                any |= ok;
            }
            if(!any) return false;
            cur = nxt;
        }
        // any end position works
        for(int i=0;i<N;i++) if(cur[i]) return true;
        return false;
    };

    auto score = [&](const Grid &g)->int{
        // Iterate k from 1 upward until first failure
        // Practical cap to avoid spending too long on extremely good grids (unlikely)
        int k = 1;
        string s;
        s.reserve(32);
        for(;;k++){
            // convert k to string
            s.clear();
            int x=k;
            while(x){
                s.push_back(char('0' + (x%10)));
                x/=10;
            }
            if(s.empty()) s="0";
            reverse(s.begin(), s.end());
            if(!readable(g, s)) return k-1;
            // time guard
            if(((double)chrono::duration_cast<chrono::duration<double>>(now()-start).count()) > max_seconds) return k-1;
        }
    };

    // Initial grid: patterned to encourage many adjacencies, then add randomness
    Grid curG, bestG, candG;
    for(int r=0;r<H;r++){
        for(int c=0;c<W;c++){
            int i=idx(r,c);
            curG.a[i] = (unsigned char)((r + 2*c + (r/2)) % 10);
        }
    }
    // sprinkle randomness
    uniform_int_distribution<int> dist_digit(0,9);
    for(int i=0;i<N;i++){
        if((rng() & 3)==0){ // 25% chance mutate initial
            curG.a[i] = (unsigned char)dist_digit(rng);
        }
    }

    int curScore = score(curG);
    bestG = curG;
    int bestScore = curScore;

    // Simulated annealing / hill climbing
    const int MAX_ITERS = 1e9; // effectively unlimited; time-limited loop
    double T0 = 5.0, T1 = 0.05;
    uniform_int_distribution<int> dist_idx(0, N-1);

    for(int iter=0; iter<MAX_ITERS; iter++){
        double elapsed = chrono::duration_cast<chrono::duration<double>>(now()-start).count();
        if(elapsed > max_seconds) break;
        double t = elapsed / max_seconds;
        double T = T0 * pow(T1/T0, t); // exponential cooling

        candG = curG;
        // propose mutation(s)
        int moves = 1 + (rng() % 2); // 1 or 2 cells
        array<int,3> changedIdx;
        array<unsigned char,3> oldVal, newVal;
        for(int m=0;m<moves;m++){
            int p = dist_idx(rng);
            unsigned char ov = candG.a[p];
            unsigned char nv = ov;
            int tries=0;
            do {
                nv = (unsigned char)dist_digit(rng);
                tries++;
            } while(nv==ov && tries<5);
            candG.a[p] = nv;
            changedIdx[m]=p;
            oldVal[m]=ov;
            newVal[m]=nv;
        }

        int sc = score(candG);

        bool accept = false;
        if(sc >= curScore){
            accept = true;
        }else{
            double delta = (double)(sc - curScore);
            double prob = exp(delta / max(1e-9, T));
            double u = (double) ( (rng()>>11) % 1000000 ) / 1000000.0;
            if(u < prob) accept = true;
        }

        if(accept){
            curG = candG;
            curScore = sc;
            if(sc > bestScore){
                bestScore = sc;
                bestG = candG;
            }
        }else{
            // revert not needed since we modified candG
        }
    }

    // Output best grid
    for(int r=0;r<H;r++){
        for(int c=0;c<W;c++){
            cout << char('0' + bestG.a[idx(r,c)]);
        }
        cout << '\n';
    }
    return 0;
}