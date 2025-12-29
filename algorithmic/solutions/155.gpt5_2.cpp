#include <bits/stdc++.h>
using namespace std;

static const int H = 20;
static const int W = 20;
static const int N = H*W;

struct Node {
    double score;     // accumulated weighted arrivals within horizon
    double key;       // score + heuristic to rank in beam
    char first;       // first move in the sequence leading here
    array<double, N> p; // distribution after this node's depth
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int si, sj, ti, tj;
    double p;
    if(!(cin >> si >> sj >> ti >> tj >> p)) {
        // Fallback: output simple string if input malformed
        cout << "DRDRDRDRDRDRDRDRDRDR" << endl;
        return 0;
    }
    vector<string> h(H);
    for(int i=0;i<H;i++) cin >> h[i];
    vector<string> v(H-1);
    for(int i=0;i<H-1;i++) cin >> v[i];

    // Build movement data
    // dir: 0=U,1=D,2=L,3=R
    int di[4] = {-1,1,0,0};
    int dj[4] = {0,0,-1,1};
    char dch[4] = {'U','D','L','R'};
    // neighbor index if open, else -1
    int neigh[N][4];
    bool openEdge[N][4];
    for(int i=0;i<H;i++){
        for(int j=0;j<W;j++){
            int idx = i*W+j;
            for(int d=0;d<4;d++){
                int ni = i + di[d];
                int nj = j + dj[d];
                bool open = false;
                if(ni>=0 && ni<H && nj>=0 && nj<W){
                    if(d==0){ // U
                        open = (i-1>=0) && (v[i-1][j]=='0');
                    }else if(d==1){ // D
                        open = (i<=H-2) && (v[i][j]=='0');
                    }else if(d==2){ // L
                        open = (j-1>=0) && (h[i][j-1]=='0');
                    }else{ // R
                        open = (j<=W-2) && (h[i][j]=='0');
                    }
                } else {
                    open = false;
                }
                openEdge[idx][d] = open;
                if(open) neigh[idx][d] = ni*W+nj;
                else neigh[idx][d] = -1;
            }
        }
    }

    // Precompute BFS distance to target
    int T = ti*W + tj;
    vector<int> dist(N, 1e9);
    deque<int> dq;
    dist[T] = 0;
    dq.push_back(T);
    while(!dq.empty()){
        int u = dq.front(); dq.pop_front();
        int ui = u / W, uj = u % W;
        for(int d=0; d<4; d++){
            int vi = ui + di[d];
            int vj = uj + dj[d];
            if(vi<0 || vi>=H || vj<0 || vj>=W) continue;
            int vidx = vi*W+vj;
            // To be able to go from vidx to u, the edge (vidx -> u) must be open in the reverse direction
            // That is, from vidx in direction opposite of d must be open.
            int rd = d ^ 1; // 0<->1, 2<->3
            if(openEdge[vidx][rd]){
                if(dist[vidx] > dist[u] + 1){
                    dist[vidx] = dist[u] + 1;
                    dq.push_back(vidx);
                }
            }
        }
    }

    auto apply_move = [&](const array<double,N>& prev, int dir, array<double,N>& next)->double{
        // returns newly reached probability mass at target in this step
        // next = transition(prev, dir)
        // absorption at T (target)
        fill(next.begin(), next.end(), 0.0);
        double massBefore = prev[T];
        next[T] += massBefore; // absorb
        for(int s=0; s<N; s++){
            if(s == T) continue;
            double ps = prev[s];
            if(ps == 0.0) continue;
            if(openEdge[s][dir]){
                int t = neigh[s][dir];
                if(t == T){
                    next[T] += ps * (1.0 - p);
                    next[s] += ps * p;
                }else{
                    next[t] += ps * (1.0 - p);
                    next[s] += ps * p;
                }
            }else{
                next[s] += ps; // blocked; stays regardless
            }
        }
        return next[T] - massBefore;
    };

    auto expected_dist = [&](const array<double,N>& prob)->double {
        double ed = 0.0;
        for(int i=0;i<N;i++){
            if(prob[i] == 0.0) continue;
            ed += prob[i] * (double)dist[i];
        }
        return ed;
    };

    // Initialize distribution
    array<double,N> cur{};
    cur.fill(0.0);
    int S = si*W + sj;
    cur[S] = 1.0;

    // If already at target
    if(S == T){
        cout << "" << '\n';
        return 0;
    }

    // Parameters
    const int LMAX = 200;
    // Beam parameters
    int BEAM = 20;
    int HORIZON = 10;
    // Heuristic weight for expected distance (tuned)
    double lambda = 1.5;

    // Slightly adjust params by p: higher p -> longer horizon, stronger heuristic
    if(p >= 0.4){
        HORIZON = 12;
        BEAM = 24;
        lambda = 2.0;
    }else if(p >= 0.25){
        HORIZON = 11;
        BEAM = 22;
        lambda = 1.7;
    }else{
        HORIZON = 10;
        BEAM = 20;
        lambda = 1.5;
    }

    string answer;
    answer.reserve(LMAX);

    // Time guard
    auto t_start = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.85; // seconds

    double totalScore = 0.0;
    for(int step = 1; step <= LMAX; step++){
        // Early terminate if almost surely at target
        if(cur[T] >= 0.999999) break;

        // Adjust horizon near end
        int rem = LMAX - step + 1;
        int Hcur = min(HORIZON, rem);

        // Beam search from current distribution
        vector<Node> curBeam;
        Node root;
        root.score = 0.0;
        root.first = '?';
        root.p = cur;
        double hroot = expected_dist(root.p);
        root.key = root.score - lambda * hroot;
        curBeam.push_back(root);

        for(int ddepth = 0; ddepth < Hcur; ddepth++){
            vector<Node> nextBeam;
            nextBeam.reserve(curBeam.size() * 4);
            for(const auto& nd : curBeam){
                for(int dir=0; dir<4; dir++){
                    Node child;
                    child.p.fill(0.0);
                    double newMass = apply_move(nd.p, dir, child.p);
                    // weight for arrivals at this absolute step
                    double weight = 401.0 - (double)(step + ddepth);
                    child.score = nd.score + weight * newMass;
                    child.first = (ddepth==0 ? dch[dir] : nd.first);
                    double heur = expected_dist(child.p);
                    child.key = child.score - lambda * heur;
                    nextBeam.push_back(std::move(child));
                }
            }
            // Keep top BEAM by key
            if((int)nextBeam.size() > BEAM){
                nth_element(nextBeam.begin(), nextBeam.begin()+BEAM, nextBeam.end(),
                    [](const Node& a, const Node& b){ return a.key > b.key; });
                nextBeam.resize(BEAM);
            }
            curBeam.swap(nextBeam);
            if(curBeam.empty()) break;
        }

        // Choose best first move among current beam by actual score
        char bestChar = 'U';
        double bestScore = -1e100;
        for(const auto& nd : curBeam){
            if(nd.score > bestScore){
                bestScore = nd.score;
                bestChar = nd.first;
            }
        }

        // As fallback (should never happen), choose direction that reduces expected distance most
        if(bestScore < -1e90){
            double bestHeur = 1e100;
            char bestC = 'U';
            for(int dir=0; dir<4; dir++){
                array<double,N> nxt{};
                double nm = apply_move(cur, dir, nxt);
                (void)nm;
                double h = expected_dist(nxt);
                if(h < bestHeur){
                    bestHeur = h;
                    bestC = dch[dir];
                }
            }
            bestChar = bestC;
        }

        // Apply chosen move to current distribution and update answer
        int cdir = 0;
        for(int d=0; d<4; d++) if(dch[d]==bestChar) { cdir = d; break; }
        array<double,N> nxt{};
        double newMass = apply_move(cur, cdir, nxt);
        totalScore += (401.0 - (double)step) * newMass;
        cur = nxt;
        answer.push_back(bestChar);

        // Time check
        auto t_now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(t_now - t_start).count();
        if(elapsed > TIME_LIMIT) break;
    }

    if(answer.size() > (size_t)LMAX) answer.resize(LMAX);
    cout << answer << '\n';
    return 0;
}