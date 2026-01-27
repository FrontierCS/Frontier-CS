#include <bits/stdc++.h>
using namespace std;

using i128 = __int128_t;
using u64 = unsigned long long;

static inline i128 iabs(i128 x){ return x < 0 ? -x : x; }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    long long Tl;
    if(!(cin >> n >> Tl)) return 0;
    vector<u64> a(n);
    for(int i=0;i<n;i++) cin >> a[i];
    i128 T = (i128)Tl;
    // Orders
    vector<int> ordDesc(n);
    iota(ordDesc.begin(), ordDesc.end(), 0);
    sort(ordDesc.begin(), ordDesc.end(), [&](int i, int j){
        if (a[i] != a[j]) return a[i] > a[j];
        return i < j;
    });
    
    // RNG and time
    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    auto start = chrono::steady_clock::now();
    const long long TIME_MS = 950;
    auto deadline = start + chrono::milliseconds(TIME_MS);
    
    // Helper lambdas
    auto compute_sum = [&](const vector<char>& bits)->i128{
        i128 s = 0;
        for(int i=0;i<n;i++) if(bits[i]) s += (i128)a[i];
        return s;
    };
    
    auto greedy_build = [&](const vector<int>& order)->vector<char>{
        vector<char> bits(n, 0);
        i128 s = 0;
        i128 r = T - s;
        for(int idx : order){
            i128 eff = (i128)a[idx];
            i128 nr = r - eff;
            if(iabs(nr) < iabs(r)){
                bits[idx] = 1;
                r = nr;
                s += eff;
            }
        }
        return bits;
    };
    
    auto local_search = [&](vector<char>& bits){
        i128 s = compute_sum(bits);
        i128 r = T - s;
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        
        // Repeated coordinate descent + 2-opt
        while (true) {
            bool changed = false;
            // One or two passes with random and descending order
            // Pass 1: random
            shuffle(order.begin(), order.end(), rng);
            for(int i : order){
                i128 eff = bits[i] ? -(i128)a[i] : (i128)a[i];
                i128 nr = r - eff;
                if(iabs(nr) < iabs(r)){
                    bits[i] ^= 1;
                    r = nr;
                    s += eff;
                    changed = true;
                }
            }
            // Pass 2: descending by value
            for(int i : ordDesc){
                i128 eff = bits[i] ? -(i128)a[i] : (i128)a[i];
                i128 nr = r - eff;
                if(iabs(nr) < iabs(r)){
                    bits[i] ^= 1;
                    r = nr;
                    s += eff;
                    changed = true;
                }
            }
            if(changed) continue;
            
            // 2-opt best pair
            vector<i128> eff(n);
            for(int i=0;i<n;i++) eff[i] = bits[i] ? -(i128)a[i] : (i128)a[i];
            i128 base = iabs(r);
            i128 best = base;
            int bi=-1,bj=-1;
            for(int i=0;i<n;i++){
                for(int j=i+1;j<n;j++){
                    i128 nr = r - (eff[i] + eff[j]);
                    i128 val = iabs(nr);
                    if(val < best){
                        best = val;
                        bi = i; bj = j;
                    }
                }
            }
            if(bi != -1){
                bits[bi] ^= 1;
                bits[bj] ^= 1;
                r = r - (eff[bi] + eff[bj]);
                s = s + (eff[bi] + eff[bj]);
                continue;
            }
            break; // no improvement
        }
    };
    
    // Initial best: greedy descending
    vector<char> best_bits = greedy_build(ordDesc);
    i128 best_sum = 0;
    for(int i=0;i<n;i++) if(best_bits[i]) best_sum += (i128)a[i];
    i128 best_diff = iabs(T - best_sum);
    
    auto consider_best = [&](const vector<char>& bits){
        i128 s = 0;
        for(int i=0;i<n;i++) if(bits[i]) s += (i128)a[i];
        i128 d = iabs(T - s);
        if(d < best_diff){
            best_diff = d;
            best_bits = bits;
        }
    };
    
    // Do local search from the greedy start
    {
        vector<char> cur = best_bits;
        local_search(cur);
        consider_best(cur);
    }
    
    // Another start: all ones
    if (chrono::steady_clock::now() < deadline) {
        vector<char> cur(n, 1);
        local_search(cur);
        consider_best(cur);
    }
    
    // Restarts until time
    int mode = 0;
    i128 sumA = 0;
    for(int i=0;i<n;i++) sumA += (i128)a[i];
    double p = 0.0;
    if (sumA > 0) {
        long double pd = (long double)(long double)( (long double)(Tl) ) / (long double) ( (long double) ( (long double) (sumA) ) );
        if (pd < 0) pd = 0;
        if (pd > 1) pd = 1;
        p = (double)pd;
    }
    uniform_real_distribution<double> U(0.0, 1.0);
    
    while (chrono::steady_clock::now() < deadline) {
        vector<char> cur(n, 0);
        if (mode % 3 == 0) {
            // Random prob p
            for(int i=0;i<n;i++) cur[i] = (U(rng) < p) ? 1 : 0;
        } else if (mode % 3 == 1) {
            // Greedy with random order
            vector<int> ord(n);
            iota(ord.begin(), ord.end(), 0);
            shuffle(ord.begin(), ord.end(), rng);
            cur = greedy_build(ord);
        } else {
            // Sparse: pick few largest fitting towards T
            i128 s = 0;
            i128 r = T - s;
            for (int idx : ordDesc) {
                if ( (iabs(r - (i128)a[idx]) <= iabs(r)) || (U(rng) < 0.1) ) {
                    cur[idx] = 1;
                    r -= (i128)a[idx];
                    s += (i128)a[idx];
                }
            }
        }
        local_search(cur);
        consider_best(cur);
        mode++;
    }
    
    // Output
    string out;
    out.reserve(n);
    for(int i=0;i<n;i++) out.push_back(best_bits[i] ? '1' : '0');
    cout << out << "\n";
    return 0;
}