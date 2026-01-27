#include <bits/stdc++.h>
using namespace std;

static inline void flush() { cout.flush(); }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if(!(cin >> t)) return 0;
    auto ask = [&](int l, int r)->int{
        cout << "? " << l << " " << r << "\n";
        flush();
        int x;
        if(!(cin >> x)) exit(0);
        return x;
    };
    auto guess = [&](int a)->int{
        cout << "! " << a << "\n";
        flush();
        int y;
        if(!(cin >> y)) exit(0);
        return y;
    };
    
    for(int _=0;_<t;_++){
        int n;
        cin >> n;
        
        auto qlimit_calc = [&](int n)->int{
            double base = 1.116;
            double ln = log((double)n);
            double lb = log(base);
            int k = (int)ceil(ln / lb);
            return 2 * k;
        };
        int QLIM = max(1, qlimit_calc(n));
        int used = 0;
        
        auto safe_ask = [&](int l, int r)->int{
            if(l<1) l=1;
            if(r>n) r=n;
            int x = ask(l,r);
            used++;
            return x;
        };
        
        int L = 1, R = n;
        const int k = 2;
        
        // Phase 1: shrink using liar-tolerant binary strategy
        while(R - L + 1 > 5 && used < QLIM) {
            int mid = (L + R) / 2;
            int x = safe_ask(1, mid);
            if(x < mid) {
                R = mid;
            } else {
                L = mid + 1;
            }
            L = max(1, L - k);
            R = min(n, R + k);
        }
        
        // Phase 2: local scanning to find candidate(s)
        int found_candidate = -1;
        
        auto find_by_delta = [&](int l, int r, int budget){
            int cand = -1;
            // Try multiple passes if budget allows
            for(int pass=0; pass<3 && used + 2 <= QLIM && budget > 0; ++pass){
                for(int m = l; m <= r-1 && used + 2 <= QLIM && budget > 0; ++m){
                    int x1 = safe_ask(1, m);
                    budget--;
                    if(used >= QLIM || budget <= 0) break;
                    int x2 = safe_ask(1, m+1);
                    budget--;
                    if(x2 - x1 == -1) {
                        cand = m+1;
                        return cand;
                    }
                }
            }
            return cand;
        };
        
        if(R - L + 1 > 0) {
            int budget = max(0, QLIM - used - 6);
            found_candidate = find_by_delta(L, R, budget);
        }
        
        if(found_candidate != -1) {
            int y = guess(found_candidate);
            if(y == 1) {
                cout << "#\n";
                flush();
                continue;
            } else {
                // second guess: choose another plausible candidate near found one
                int a2 = found_candidate;
                if(a2 < R) a2++;
                else if(a2 > L) a2--;
                else a2 = max(1, min(n, found_candidate ^ 1 ? found_candidate ^ 1 : found_candidate)); // fallback
                (void)guess(a2);
                cout << "#\n";
                flush();
                continue;
            }
        } else {
            // Fallback: guess two central positions within [L, R] or [1, n] if degenerate
            int a = (L + R) / 2;
            if(a < 1) a = 1;
            if(a > n) a = n;
            int y = guess(a);
            if(y == 1) {
                cout << "#\n";
                flush();
                continue;
            } else {
                int b = a + 1;
                if(b > R) b = a - 1;
                if(b < 1) b = min(n, a + 2);
                if(b < 1 || b > n || b == a) b = (a == 1 ? 2 : 1);
                (void)guess(b);
                cout << "#\n";
                flush();
                continue;
            }
        }
    }
    return 0;
}