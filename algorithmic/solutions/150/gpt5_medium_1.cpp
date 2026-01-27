#include <bits/stdc++.h>
using namespace std;

static const int N = 20;
static const int KMIN = 2;
static const int KMAX = 12;
static const int KRANGE = KMAX - KMIN + 1;

struct RNG {
    uint64_t x;
    RNG(uint64_t seed=88172645463393265ull){ x = seed; }
    inline uint64_t nextU64() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    inline int nextInt(int l, int r) { // inclusive
        return int(l + (nextU64() % (uint64_t)(r - l + 1)));
    }
    inline double nextDouble() {
        // 53-bit resolution
        return (nextU64() >> 11) * (1.0 / 9007199254740992.0);
    }
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n_in, M;
    if(!(cin >> n_in >> M)) {
        return 0;
    }
    vector<string> s(M);
    for(int i=0;i<M;i++) cin >> s[i];

    // Hash parameters
    RNG rng(1234567891234567ull);
    uint64_t B = 1469598103934665603ull ^ rng.nextU64() | 1ull; // odd base
    uint64_t Cval[8];
    for(int i=0;i<8;i++) {
        uint64_t v = rng.nextU64();
        if(v == 0) v = 1;
        Cval[i] = v;
    }

    auto char2idx = [](char ch)->int { return ch - 'A'; };

    auto hash_str = [&](const string &t)->uint64_t{
        uint64_t h = 0;
        for(char ch : t) {
            h = h * B + Cval[char2idx(ch)];
        }
        return h;
    };

    // Group sizes per (k, hash)
    array<unordered_map<uint64_t,int>, KRANGE> groupSize;
    for(int kidx=0;kidx<KRANGE;kidx++){
        groupSize[kidx].reserve(M*2);
    }
    for(int i=0;i<M;i++){
        int k = (int)s[i].size();
        uint64_t h = hash_str(s[i]);
        groupSize[k-KMIN][h]++;
    }

    // Grid as ints 0..7
    static uint8_t grid[N][N];

    // Initialize grid randomly
    for(int i=0;i<N;i++){
        for(int j=0;j<N;j++){
            grid[i][j] = (uint8_t)rng.nextInt(0,7);
        }
    }

    // Stored substring hashes: dims 2 (0=row,1=col), idx 20, k 11, start 20
    const int HSIZE = 2 * N * KRANGE * N;
    vector<uint64_t> stored(HSIZE);

    auto H_index = [&](int dim, int idx, int kidx, int start)->int{
        // (((dim * N + idx) * KRANGE + kidx) * N + start)
        return (((dim * N + idx) * KRANGE + kidx) * N + start);
    };

    auto compute_sub_hash_new = [&](int dim, int idx, int start, int k, int chg_r, int chg_c, uint8_t newVal)->uint64_t{
        uint64_t h = 0;
        if(dim == 0){
            int r = idx;
            for(int p=0;p<k;p++){
                int c = (start + p) % N;
                uint8_t v = (r == chg_r && c == chg_c) ? newVal : grid[r][c];
                h = h * B + Cval[v];
            }
        }else{
            int c = idx;
            for(int p=0;p<k;p++){
                int r = (start + p) % N;
                uint8_t v = (r == chg_r && c == chg_c) ? newVal : grid[r][c];
                h = h * B + Cval[v];
            }
        }
        return h;
    };
    auto compute_sub_hash = [&](int dim, int idx, int start, int k)->uint64_t{
        uint64_t h = 0;
        if(dim == 0){
            int r = idx;
            for(int p=0;p<k;p++){
                int c = (start + p) % N;
                uint8_t v = grid[r][c];
                h = h * B + Cval[v];
            }
        }else{
            int c = idx;
            for(int p=0;p<k;p++){
                int r = (start + p) % N;
                uint8_t v = grid[r][c];
                h = h * B + Cval[v];
            }
        }
        return h;
    };

    // mapCount per k
    array<unordered_map<uint64_t,int>, KRANGE> mapCount;
    for(int kidx=0;kidx<KRANGE;kidx++){
        mapCount[kidx].reserve(2000);
    }

    // Initialize stored hashes and counts
    for(int dim=0; dim<2; dim++){
        for(int idx=0; idx<N; idx++){
            for(int kidx=0; kidx<KRANGE; kidx++){
                int k = KMIN + kidx;
                for(int start=0; start<N; start++){
                    uint64_t h = compute_sub_hash(dim, idx, start, k);
                    stored[H_index(dim, idx, kidx, start)] = h;
                    mapCount[kidx][h] += 1;
                }
            }
        }
    }

    // Compute initial c
    long long c = 0;
    for(int kidx=0;kidx<KRANGE;kidx++){
        for(auto &e : groupSize[kidx]){
            auto it = mapCount[kidx].find(e.first);
            if(it != mapCount[kidx].end() && it->second > 0){
                c += e.second;
            }
        }
    }

    // Simulated annealing
    auto startTime = chrono::steady_clock::now();
    double timeLimit = 1.9;
    auto now = startTime;
    double elapsed = 0.0;

    long long bestC = c;
    static uint8_t bestGrid[N][N];
    for(int i=0;i<N;i++) for(int j=0;j<N;j++) bestGrid[i][j] = grid[i][j];

    const double T0 = 1.0, T1 = 0.01;

    // Temporary structures
    array<unordered_map<uint64_t,int>, KRANGE> delta;
    for(int kidx=0;kidx<KRANGE;kidx++){
        delta[kidx].reserve(512);
    }

    struct Item { uint8_t dim, idx, kidx, start; uint64_t newh; };
    vector<Item> items;
    items.reserve(400);

    long long iters = 0;

    while(true){
        iters++;
        if((iters & 0x3FF) == 0){
            now = chrono::steady_clock::now();
            elapsed = chrono::duration<double>(now - startTime).count();
            if(elapsed > timeLimit) break;
        }
        double progress = elapsed / timeLimit;
        if(progress < 0) progress = 0;
        if(progress > 1) progress = 1;
        double T = T0 + (T1 - T0) * progress;

        int r = rng.nextInt(0, N-1);
        int ccol = rng.nextInt(0, N-1);
        uint8_t oldVal = grid[r][ccol];
        uint8_t newVal = (uint8_t)rng.nextInt(0,7);
        if(newVal == oldVal) newVal = (uint8_t)((newVal + 1) & 7);

        // Clear temp
        for(int kidx=0;kidx<KRANGE;kidx++) delta[kidx].clear();
        items.clear();

        // Row dimension
        {
            int dim = 0, idx = r;
            for(int kidx=0;kidx<KRANGE;kidx++){
                int k = KMIN + kidx;
                for(int t=0;t<k;t++){
                    int start = (ccol - t);
                    if(start < 0) start += N;
                    int pos = H_index(dim, idx, kidx, start);
                    uint64_t oldh = stored[pos];
                    uint64_t newh = compute_sub_hash_new(dim, idx, start, k, r, ccol, newVal);
                    if(oldh != newh){
                        delta[kidx][oldh] -= 1;
                        delta[kidx][newh] += 1;
                        items.push_back({(uint8_t)dim, (uint8_t)idx, (uint8_t)kidx, (uint8_t)start, newh});
                    }
                }
            }
        }
        // Col dimension
        {
            int dim = 1, idx = ccol;
            for(int kidx=0;kidx<KRANGE;kidx++){
                int k = KMIN + kidx;
                for(int t=0;t<k;t++){
                    int start = (r - t);
                    if(start < 0) start += N;
                    int pos = H_index(dim, idx, kidx, start);
                    uint64_t oldh = stored[pos];
                    uint64_t newh = compute_sub_hash_new(dim, idx, start, k, r, ccol, newVal);
                    if(oldh != newh){
                        delta[kidx][oldh] -= 1;
                        delta[kidx][newh] += 1;
                        items.push_back({(uint8_t)dim, (uint8_t)idx, (uint8_t)kidx, (uint8_t)start, newh});
                    }
                }
            }
        }

        // Compute deltaC
        long long deltaC = 0;
        for(int kidx=0;kidx<KRANGE;kidx++){
            if(delta[kidx].empty()) continue;
            auto &mc = mapCount[kidx];
            auto &gs = groupSize[kidx];
            for(auto &pr : delta[kidx]){
                if(pr.second == 0) continue;
                uint64_t h = pr.first;
                int d = pr.second;
                int prev = 0;
                auto it = mc.find(h);
                if(it != mc.end()) prev = it->second;
                int next = prev + d;
                if(prev <= 0 && next > 0){
                    auto it2 = gs.find(h);
                    if(it2 != gs.end()) deltaC += it2->second;
                }else if(prev > 0 && next <= 0){
                    auto it2 = gs.find(h);
                    if(it2 != gs.end()) deltaC -= it2->second;
                }
            }
        }

        bool accept = false;
        if(deltaC >= 0) accept = true;
        else {
            double prob = exp((double)deltaC / T);
            if(prob > rng.nextDouble()) accept = true;
        }

        if(accept){
            grid[r][ccol] = newVal;
            // apply stored updates
            for(const auto &it : items){
                int pos = H_index(it.dim, it.idx, it.kidx, it.start);
                stored[pos] = it.newh;
            }
            // apply counts
            for(int kidx=0;kidx<KRANGE;kidx++){
                if(delta[kidx].empty()) continue;
                auto &mc = mapCount[kidx];
                for(auto &pr : delta[kidx]){
                    if(pr.second == 0) continue;
                    uint64_t h = pr.first;
                    int d = pr.second;
                    int prev = 0;
                    auto it = mc.find(h);
                    if(it != mc.end()){
                        prev = it->second + d;
                        if(prev == 0){
                            mc.erase(it);
                        }else{
                            it->second = prev;
                        }
                    }else{
                        // prev zero
                        if(d != 0){
                            mc.emplace(h, d);
                        }
                    }
                }
            }
            c += deltaC;
            if(c > bestC){
                bestC = c;
                for(int i=0;i<N;i++) for(int j=0;j<N;j++) bestGrid[i][j] = grid[i][j];
            }
        }
    }

    // Output best grid
    for(int i=0;i<N;i++){
        string line;
        line.resize(N);
        for(int j=0;j<N;j++){
            line[j] = char('A' + bestGrid[i][j]);
        }
        cout << line << '\n';
    }
    return 0;
}