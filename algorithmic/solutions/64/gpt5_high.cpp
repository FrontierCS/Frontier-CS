#include <bits/stdc++.h>
using namespace std;

using i64 = long long;
static inline i64 absl(i64 x){ return x<0?-x:x; }

struct Solver {
    int n;
    i64 T;
    vector<i64> a;

    mt19937_64 rng;

    Solver(int n, i64 T, const vector<i64>& a): n(n), T(T), a(a) {
        rng.seed(chrono::high_resolution_clock::now().time_since_epoch().count());
    }

    vector<char> mitm_exact() {
        int m = n/2;
        int r = n - m;
        int Lsz = 1 << m;
        int Rsz = 1 << r;

        vector<i64> leftVals(m), rightVals(r);
        for(int i=0;i<m;i++) leftVals[i]=a[i];
        for(int i=0;i<r;i++) rightVals[i]=a[m+i];

        vector<pair<i64, uint32_t>> L; L.reserve(Lsz);
        vector<pair<i64, uint32_t>> R; R.reserve(Rsz);

        // enumerate left
        vector<i64> sumL(Lsz);
        sumL[0]=0;
        for(int mask=1; mask<Lsz; ++mask){
            int lb = mask & -mask;
            int idx = __builtin_ctz((unsigned)lb);
            sumL[mask] = sumL[mask ^ lb] + leftVals[idx];
        }
        for(int mask=0; mask<Lsz; ++mask){
            L.emplace_back(sumL[mask], (uint32_t)mask);
        }

        // enumerate right
        vector<i64> sumR(Rsz);
        sumR[0]=0;
        for(int mask=1; mask<Rsz; ++mask){
            int lb = mask & -mask;
            int idx = __builtin_ctz((unsigned)lb);
            sumR[mask] = sumR[mask ^ lb] + rightVals[idx];
        }
        for(int mask=0; mask<Rsz; ++mask){
            R.emplace_back(sumR[mask], (uint32_t)mask);
        }

        sort(R.begin(), R.end(), [](const auto& x, const auto& y){ return x.first < y.first; });

        i64 bestErr = (1LL<<62);
        uint32_t bestLm=0, bestRm=0;

        for(const auto& [sL, maskL] : L){
            i64 target = T - sL;
            auto it = lower_bound(R.begin(), R.end(), make_pair(target, (uint32_t)0), [](const auto& x, const auto& y){ return x.first < y.first; });
            if(it != R.end()){
                i64 sR = it->first;
                i64 err = absl((sL + sR) - T);
                if(err < bestErr){
                    bestErr = err; bestLm = maskL; bestRm = it->second;
                    if(bestErr==0) break;
                }
            }
            if(it != R.begin()){
                --it;
                i64 sR = it->first;
                i64 err = absl((sL + sR) - T);
                if(err < bestErr){
                    bestErr = err; bestLm = maskL; bestRm = it->second;
                }
            }
        }

        vector<char> res(n, 0);
        for(int i=0;i<m;i++){
            if(bestLm & (1u<<i)) res[i]=1;
        }
        for(int i=0;i<r;i++){
            if(bestRm & (1u<<i)) res[m+i]=1;
        }
        return res;
    }

    struct Solution {
        vector<char> bits;
        i64 sum;
        i64 err;
    };

    i64 compute_sum(const vector<char>& bits){
        __int128 s=0;
        for(int i=0;i<n;i++) if(bits[i]) s += a[i];
        i64 ss = (i64)s;
        return ss;
    }

    Solution make_solution(const vector<char>& bits){
        i64 s = compute_sum(bits);
        return {bits, s, absl(s - T)};
    }

    Solution greedy_desc() {
        vector<int> idx(n);
        iota(idx.begin(), idx.end(), 0);
        sort(idx.begin(), idx.end(), [&](int i, int j){ return a[i] > a[j]; });
        vector<char> bits(n, 0);
        i64 sum = 0;
        for(int id: idx){
            if(sum + a[id] <= T){
                bits[id] = 1;
                sum += a[id];
            }
        }
        return {bits, sum, absl(sum - T)};
    }

    Solution single_item() {
        int besti = 0;
        i64 bestErr = absl(a[0] - T);
        for(int i=1;i<n;i++){
            i64 err = absl(a[i] - T);
            if(err < bestErr){
                bestErr = err;
                besti = i;
            }
        }
        vector<char> bits(n, 0);
        bits[besti] = 1;
        i64 sum = a[besti];
        return {bits, sum, absl(sum - T)};
    }

    Solution greedy_randomized() {
        vector<int> idx(n);
        iota(idx.begin(), idx.end(), 0);
        shuffle(idx.begin(), idx.end(), rng);
        vector<char> bits(n, 0);
        i64 sum = 0;
        for(int id: idx){
            i64 newSum = sum + a[id];
            if(absl(newSum - T) <= absl(sum - T)){
                bits[id] = 1;
                sum = newSum;
            }
        }
        return {bits, sum, absl(sum - T)};
    }

    Solution random_prob(double p) {
        vector<char> bits(n, 0);
        uniform_real_distribution<double> dist(0.0, 1.0);
        i64 sum = 0;
        for(int i=0;i<n;i++){
            if(dist(rng) < p){
                bits[i] = 1;
                sum += a[i];
            }
        }
        return {bits, sum, absl(sum - T)};
    }

    void local_search(Solution& sol, const chrono::steady_clock::time_point& deadline) {
        vector<char>& bits = sol.bits;
        i64& sum = sol.sum;
        while(chrono::steady_clock::now() < deadline){
            i64 D = sum - T;
            i64 curErr = absl(D);

            // Single flip best improvement
            int besti = -1;
            i64 bestErr = curErr;
            for(int i=0;i<n;i++){
                i64 newD = D + (bits[i] ? -a[i] : a[i]);
                i64 newErr = absl(newD);
                if(newErr < bestErr){
                    bestErr = newErr;
                    besti = i;
                }
            }
            if(besti != -1){
                sum += (bits[besti] ? -a[besti] : a[besti]);
                bits[besti] ^= 1;
                sol.err = absl(sum - T);
                continue;
            }

            // Pair flip best improvement
            if(chrono::steady_clock::now() >= deadline) break;
            vector<i64> delta(n);
            for(int i=0;i<n;i++) delta[i] = (bits[i] ? -a[i] : a[i]);

            int pi=-1, pj=-1;
            bestErr = curErr;
            for(int i=0;i<n;i++){
                for(int j=i+1;j<n;j++){
                    i64 newD = D + delta[i] + delta[j];
                    i64 newErr = absl(newD);
                    if(newErr < bestErr){
                        bestErr = newErr;
                        pi = i; pj = j;
                    }
                }
                if((i & 7) == 0 && chrono::steady_clock::now() >= deadline) break;
            }
            if(pi != -1){
                sum += delta[pi] + delta[pj];
                bits[pi] ^= 1;
                bits[pj] ^= 1;
                sol.err = absl(sum - T);
                continue;
            }
            break; // no improvement
        }
        sol.err = absl(sum - T);
    }

    string solve() {
        if(n <= 40){
            vector<char> res = mitm_exact();
            string s; s.reserve(n);
            for(int i=0;i<n;i++) s.push_back(res[i] ? '1' : '0');
            return s;
        }

        auto start = chrono::steady_clock::now();
        // Allow around 0.95s time budget
        double seconds = 0.95;
        auto deadline = start + chrono::duration<double>(seconds);

        i64 sumAll = 0;
        for(auto v: a) sumAll += v;
        double p0 = 0.0;
        if(sumAll > 0) {
            long double pp = (long double)T / (long double)sumAll;
            if(pp < 0) pp = 0;
            if(pp > 1) pp = 1;
            p0 = (double)pp;
        }

        Solution best = greedy_desc();
        if(best.err == 0) {
            string s; s.reserve(n);
            for(int i=0;i<n;i++) s.push_back(best.bits[i] ? '1' : '0');
            return s;
        }
        Solution s1 = single_item();
        if(s1.err < best.err) best = s1;
        Solution s2 = greedy_randomized();
        if(s2.err < best.err) best = s2;

        // Improve these seeds
        local_search(best, deadline);
        if(best.err == 0){
            string out; out.reserve(n);
            for(int i=0;i<n;i++) out.push_back(best.bits[i] ? '1' : '0');
            return out;
        }

        if(chrono::steady_clock::now() < deadline){
            local_search(s1, deadline);
            if(s1.err < best.err) best = s1;
        }
        if(chrono::steady_clock::now() < deadline){
            local_search(s2, deadline);
            if(s2.err < best.err) best = s2;
        }

        // Random restarts
        int iter = 0;
        while(chrono::steady_clock::now() < deadline){
            Solution rnd = random_prob(p0);
            local_search(rnd, deadline);
            if(rnd.err < best.err) best = rnd;
            if(++iter % 3 == 0 && chrono::steady_clock::now() < deadline){
                Solution rg = greedy_randomized();
                local_search(rg, deadline);
                if(rg.err < best.err) best = rg;
            }
            if(best.err == 0) break;
        }

        string out; out.reserve(n);
        for(int i=0;i<n;i++) out.push_back(best.bits[i] ? '1' : '0');
        return out;
    }
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    long long T;
    if(!(cin >> n >> T)) {
        return 0;
    }
    vector<long long> a(n);
    for(int i=0;i<n;i++) cin >> a[i];

    Solver solver(n, T, a);
    string ans = solver.solve();
    cout << ans << '\n';
    return 0;
}