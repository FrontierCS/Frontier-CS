#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if(!(cin >> N)) return 0;
    int r0, c0;
    cin >> r0 >> c0;
    --r0; --c0;

    const int dr[8] = {-2,-2,-1,-1,1,1,2,2};
    const int dc[8] = {-1,1,-2,2,-2,2,-1,1};

    auto inb = [&](int r,int c){ return (r>=0 && r<N && c>=0 && c<N); };

    vector<pair<int,int>> bestPath;
    bestPath.reserve(1LL*N*N);
    int bestLen = 0;

    vector<vector<unsigned char>> vis(N, vector<unsigned char>(N, 0));
    vector<pair<int,int>> path;
    path.reserve(1LL*N*N);

    std::mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    auto now = [&](){ return chrono::steady_clock::now(); };
    auto startTime = now();
    auto elapsed_ms = [&](){
        return chrono::duration_cast<chrono::milliseconds>(now() - startTime).count();
    };

    auto degree = [&](int r, int c)->int{
        int cnt = 0;
        for(int k=0;k<8;k++){
            int nr = r + dr[k], nc = c + dc[k];
            if(inb(nr,nc) && !vis[nr][nc]) cnt++;
        }
        return cnt;
    };

    auto second_criterion = [&](int r, int c)->int{
        // minimal degree among neighbors of (r,c)
        int best = 9;
        for(int k=0;k<8;k++){
            int nr = r + dr[k], nc = c + dc[k];
            if(inb(nr,nc) && !vis[nr][nc]) {
                int d = 0;
                for(int t=0;t<8;t++){
                    int tr = nr + dr[t], tc = nc + dc[t];
                    if(inb(tr,tc) && !vis[tr][tc]) d++;
                }
                best = min(best, d);
            }
        }
        if(best==9) best = 0;
        return best;
    };

    // Attempt until success or time runs out
    int maxAttempts = 1000000; // effectively time-bound
    for(int attempt=0; attempt<maxAttempts; ++attempt){
        if(bestLen == N*1LL*N) break;
        if(elapsed_ms() > 950) break;

        // reset
        for(int i=0;i<N;i++) memset(vis[i].data(), 0, N*sizeof(unsigned char));
        path.clear();

        int r = r0, c = c0;
        vis[r][c] = 1;
        path.emplace_back(r, c);

        bool failed = false;
        for(long long step = 1; step < 1LL*N*N; ++step){
            int minDeg = 9;
            vector<pair<int,int>> cand;
            cand.reserve(8);
            for(int k=0;k<8;k++){
                int nr = r + dr[k], nc = c + dc[k];
                if(inb(nr,nc) && !vis[nr][nc]){
                    int d = 0;
                    for(int t=0;t<8;t++){
                        int tr = nr + dr[t], tc = nc + dc[t];
                        if(inb(tr,tc) && !vis[tr][tc]) d++;
                    }
                    if(d < minDeg){
                        minDeg = d;
                        cand.clear();
                        cand.emplace_back(nr,nc);
                    }else if(d == minDeg){
                        cand.emplace_back(nr,nc);
                    }
                }
            }
            if(cand.empty()){
                failed = true;
                break;
            }
            // Tie-breaker: choose with minimal second criterion; if still tie, random
            int best2 = 10;
            vector<pair<int,int>> cand2;
            cand2.reserve(cand.size());
            for(auto &p : cand){
                int sc = 0;
                // compute minimal onward degree from this candidate
                int min2 = 9;
                for(int t=0;t<8;t++){
                    int tr = p.first + dr[t], tc = p.second + dc[t];
                    if(inb(tr,tc) && !vis[tr][tc]){
                        int d2 = 0;
                        for(int u=0;u<8;u++){
                            int xr = tr + dr[u], xc = tc + dc[u];
                            if(inb(xr,xc) && !vis[xr][xc]) d2++;
                        }
                        if(d2 < min2) min2 = d2;
                    }
                }
                sc = (min2==9)?0:min2;
                if(sc < best2){
                    best2 = sc;
                    cand2.clear();
                    cand2.push_back(p);
                }else if(sc == best2){
                    cand2.push_back(p);
                }
            }
            pair<int,int> next;
            if(cand2.size()==1) {
                next = cand2[0];
            } else {
                next = cand2[rng() % cand2.size()];
            }
            r = next.first; c = next.second;
            vis[r][c] = 1;
            path.emplace_back(r, c);
        }

        if((int)path.size() > bestLen){
            bestLen = (int)path.size();
            bestPath = path;
        }
        if(!failed && (int)path.size() == N*1LL*N){
            // Full tour found
            break;
        }
    }

    cout << bestLen << '\n';
    for(size_t i=0;i<bestPath.size();++i){
        cout << (bestPath[i].first+1) << ' ' << (bestPath[i].second+1);
        if(i+1<bestPath.size()) cout << '\n';
    }
    return 0;
}