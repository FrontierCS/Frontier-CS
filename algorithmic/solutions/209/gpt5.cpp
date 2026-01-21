#include <bits/stdc++.h>
using namespace std;

using i64 = long long;
using i128 = __int128_t;
using u128 = __uint128_t;

static const i64 PRIMES[3] = {1000000007LL, 1000000009LL, 998244353LL};

i64 mod_add(i64 a, i64 b, i64 mod){ a+=b; if(a>=mod) a-=mod; return a; }
i64 mod_sub(i64 a, i64 b, i64 mod){ a-=b; if(a<0) a+=mod; return a; }
i64 mod_mul(i64 a, i64 b, i64 mod){ return (i64)((__int128)a*b % mod); }
i64 mod_pow(i64 a, i64 e, i64 mod){
    i64 r=1%mod;
    while(e){
        if(e&1) r=mod_mul(r,a,mod);
        a=mod_mul(a,a,mod);
        e>>=1;
    }
    return r;
}
i64 mod_inv(i64 a, i64 mod){ return mod_pow(a, mod-2, mod); }

// Gaussian elimination to compute rank modulo mod for h x k matrix
int rank_mod(const vector<vector<i64>>& M, i64 mod){
    int h = (int)M.size();
    if(h==0) return 0;
    int k = (int)M[0].size();
    vector<vector<i64>> a = M;
    int r = 0;
    for(int c=0;c<k && r<h;c++){
        int piv = -1;
        for(int i=r;i<h;i++){
            if(a[i][c]%mod) { piv=i; break; }
        }
        if(piv==-1) continue;
        swap(a[r], a[piv]);
        i64 inv = mod_inv((a[r][c]%mod+mod)%mod, mod);
        for(int j=c;j<k;j++){
            a[r][j] = mod_mul(a[r][j], inv, mod);
        }
        for(int i=0;i<h;i++){
            if(i==r) continue;
            if(a[i][c]%mod){
                i64 factor = (a[i][c]%mod+mod)%mod;
                for(int j=c;j<k;j++){
                    i64 val = mod_sub(a[i][j], mod_mul(factor, a[r][j], mod), mod);
                    a[i][j]=val;
                }
            }
        }
        r++;
    }
    return r;
}

// Solve M (h x h) * x = b modulo mod
bool solve_mod(vector<vector<i64>> M, vector<i64> b, i64 mod, vector<i64>& x){
    int n = (int)M.size();
    // augmented matrix
    for(int i=0;i<n;i++) M[i].push_back((b[i]%mod+mod)%mod);
    int r = 0;
    vector<int> where(n, -1);
    for(int c=0;c<n && r<n;c++){
        int piv = -1;
        for(int i=r;i<n;i++){
            if(M[i][c]%mod) { piv=i; break; }
        }
        if(piv==-1) continue;
        swap(M[r], M[piv]);
        where[c] = r;
        i64 inv = mod_inv((M[r][c]%mod+mod)%mod, mod);
        for(int j=c;j<=n;j++){
            M[r][j] = mod_mul(M[r][j], inv, mod);
        }
        for(int i=0;i<n;i++){
            if(i==r) continue;
            if(M[i][c]%mod){
                i64 factor = (M[i][c]%mod+mod)%mod;
                for(int j=c;j<=n;j++){
                    M[i][j] = mod_sub(M[i][j], mod_mul(factor, M[r][j], mod), mod);
                }
            }
        }
        r++;
    }
    // check consistency
    for(int i=0;i<n;i++){
        bool allZero = true;
        for(int j=0;j<n;j++){
            if(M[i][j]%mod){ allZero=false; break; }
        }
        if(allZero && (M[i][n]%mod)){
            return false; // no solution
        }
    }
    x.assign(n, 0);
    for(int j=0;j<n;j++){
        if(where[j]!=-1){
            x[j] = (M[where[j]][n]%mod+mod)%mod;
        }else{
            x[j] = 0; // free var, but should not happen in full-rank case
        }
    }
    return true;
}

// Combine x ≡ r1 mod m1 and x ≡ r2 mod m2 into x ≡ res mod lcm=m1*m2 (assuming m1,m2 coprime)
pair<u128, u128> crt_combine(u128 r1, u128 m1, u128 r2, u128 m2){
    // Solve: r = r1 + m1 * t; Need r ≡ r2 (mod m2) => m1*t ≡ r2-r1 (mod m2)
    i64 mm1 = (i64)(m1 % m2);
    i64 rr = (i64)((r2 % m2 - r1 % m2 + m2) % m2);
    i64 inv = mod_inv((mm1 + (i64)m2)% (i64)m2, (i64)m2);
    i64 t = mod_mul(rr, inv, (i64)m2);
    u128 res = r1 + m1 * (u128)t;
    u128 mod = m1 * m2;
    res %= mod;
    return {res, mod};
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int h;
    if(!(cin >> h)) {
        return 0;
    }
    int H = h - 1;
    long long n = (1LL<<h) - 1;
    int Dmax = 2*H;

    // Precompute deg(d, t) for t=0..H, d=1..Dmax
    vector<vector<long long>> deg(H+1, vector<long long>(Dmax+1, 0));
    for(int t=0;t<=H;t++){
        for(int d=1; d<=Dmax; d++){
            long long res = 0;
            int down = H - t;
            if(d <= down){
                res += (1LL<<d);
            }
            int minj = 1;
            int maxj = min(d-1, t);
            for(int j=minj; j<=maxj; j++){
                int L = d - j;
                int height_from_w = H - (t - j);
                if(L >= 1 && L <= height_from_w){
                    res += (1LL<<(L-1));
                }
            }
            if(d <= t){
                res += 1;
            }
            deg[t][d] = res;
        }
    }

    // Select h distances 1..Dmax such that matrix (h x h) is invertible modulo all primes
    vector<int> selected;
    vector<int> candidates(Dmax);
    iota(candidates.begin(), candidates.end(), 1);

    for(int step=0; step<h; step++){
        bool found = false;
        for(int d : candidates){
            if(find(selected.begin(), selected.end(), d) != selected.end()) continue;
            // Build trial matrix columns
            int newCols = (int)selected.size() + 1;
            vector<vector<i64>> M[3];
            for(int pi=0;pi<3;pi++){
                M[pi].assign(h, vector<i64>(newCols, 0));
                for(int t=0;t<h;t++){
                    for(int c=0;c<newCols-1;c++){
                        M[pi][t][c] = (deg[t][selected[c]] % PRIMES[pi] + PRIMES[pi]) % PRIMES[pi];
                    }
                    M[pi][t][newCols-1] = (deg[t][d] % PRIMES[pi] + PRIMES[pi]) % PRIMES[pi];
                }
            }
            bool ok = true;
            for(int pi=0;pi<3;pi++){
                if(rank_mod(M[pi], PRIMES[pi]) != newCols){
                    ok = false; break;
                }
            }
            if(ok){
                selected.push_back(d);
                found = true;
                break;
            }
        }
        if(!found){
            // Fallback: just pick remaining smallest (though may fail, but try)
            for(int d : candidates){
                if(find(selected.begin(), selected.end(), d) == selected.end()){
                    selected.push_back(d);
                    break;
                }
            }
        }
    }

    // Ensure we have exactly h distances
    if((int)selected.size() > h) selected.resize(h);
    if((int)selected.size() < h){
        // pad arbitrarily (should not happen)
        for(int d=1; d<=Dmax && (int)selected.size()<h; d++){
            if(find(selected.begin(), selected.end(), d) == selected.end()){
                selected.push_back(d);
            }
        }
    }

    // Prepare to accumulate A_i mod primes
    int m = h;
    vector<array<i64,3>> A_mod(m);
    for(int i=0;i<m;i++) A_mod[i] = {0,0,0};

    // Query for each selected distance
    for(int i=0;i<m;i++){
        int d = selected[i];
        for(long long u=1; u<=n; u++){
            cout << "? " << u << " " << d << endl;
            long long ans; 
            if(!(cin >> ans)) ans = 0;
            for(int pi=0;pi<3;pi++){
                i64 mod = PRIMES[pi];
                i64 val = ((ans % mod) + mod) % mod;
                A_mod[i][pi] = mod_add(A_mod[i][pi], val, mod);
            }
        }
    }

    // Build M for solving and compute coefficients c modulo each prime
    vector<vector<i64>> c_mod(3, vector<i64>(m, 0));
    for(int pi=0;pi<3;pi++){
        i64 mod = PRIMES[pi];
        vector<vector<i64>> M(h, vector<i64>(h, 0));
        vector<i64> b(h, 1 % mod);
        for(int t=0;t<h;t++){
            for(int j=0;j<h;j++){
                M[t][j] = (deg[t][selected[j]] % mod + mod) % mod;
            }
        }
        vector<i64> sol;
        bool ok = solve_mod(M, b, mod, sol);
        if(!ok){
            // As a fallback (should not happen), set all coefficients equal 0
            for(int j=0;j<h;j++) c_mod[pi][j] = 0;
        }else{
            for(int j=0;j<h;j++) c_mod[pi][j] = (sol[j]%mod+mod)%mod;
        }
    }

    // Compute S modulo each prime
    i64 S_mod[3];
    for(int pi=0;pi<3;pi++){
        i64 mod = PRIMES[pi];
        i64 Sp = 0;
        for(int i=0;i<m;i++){
            Sp = mod_add(Sp, mod_mul(c_mod[pi][i], A_mod[i][pi], mod), mod);
        }
        S_mod[pi] = Sp;
    }

    // Reconstruct S via CRT
    u128 r = (u128)((S_mod[0] % PRIMES[0] + PRIMES[0]) % PRIMES[0]);
    u128 m1 = (u128)PRIMES[0];
    auto p12 = crt_combine(r, m1, (u128)((S_mod[1]%PRIMES[1]+PRIMES[1])%PRIMES[1]), (u128)PRIMES[1]);
    auto p123 = crt_combine(p12.first, p12.second, (u128)((S_mod[2]%PRIMES[2]+PRIMES[2])%PRIMES[2]), (u128)PRIMES[2]);
    u128 S_u128 = p123.first; // actual S is guaranteed < product of primes

    unsigned long long S_final = (unsigned long long)(S_u128); // S <= n * 1e9 fits 64-bit

    cout << "! " << S_final << endl;
    return 0;
}