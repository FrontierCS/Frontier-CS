#include <bits/stdc++.h>
using namespace std;

using u64 = unsigned long long;
using u128 = __uint128_t;

static mt19937_64 rng((u64)chrono::high_resolution_clock::now().time_since_epoch().count());

u64 rand_u64(u64 lo, u64 hi){ // inclusive
    uniform_int_distribution<u64> dist(lo, hi);
    return dist(rng);
}

u64 mul_mod(u64 a, u64 b, u64 mod){
    return (u128)a * b % mod;
}
u64 pow_mod(u64 a, u64 e, u64 mod){
    u64 r = 1;
    while(e){
        if(e & 1) r = mul_mod(r, a, mod);
        a = mul_mod(a, a, mod);
        e >>= 1;
    }
    return r;
}
bool isPrimeDet(u64 n){
    if(n < 2) return false;
    for(u64 p: {2ULL,3ULL,5ULL,7ULL,11ULL,13ULL,17ULL,19ULL,23ULL,29ULL,31ULL,37ULL}){
        if(n%p==0) return n==p;
    }
    u64 d = n-1, s = 0;
    while((d&1)==0){ d >>= 1; ++s; }
    // Deterministic bases for 64-bit
    for(u64 a: {2ULL, 3ULL, 5ULL, 7ULL, 11ULL, 13ULL}){
        if(a % n == 0) continue;
        u64 x = pow_mod(a, d, n);
        if(x == 1 || x == n-1) continue;
        bool comp = true;
        for(u64 r=1; r<s; ++r){
            x = mul_mod(x, x, n);
            if(x == n-1){ comp = false; break; }
        }
        if(comp) return false;
    }
    return true;
}
u64 pollard(u64 n){
    if((n&1ULL)==0ULL) return 2;
    if(n % 3ULL == 0ULL) return 3;
    u64 c = rand_u64(1, n-1);
    u64 x = rand_u64(2, n-2);
    u64 y = x;
    u64 d = 1;
    auto f = [&](u64 x){ return (mul_mod(x, x, n) + c) % n; };
    while(d == 1){
        x = f(x);
        y = f(f(y));
        u64 diff = x>y ? x-y : y-x;
        d = std::gcd(diff, n);
        if(d == n) return pollard(n);
    }
    return d;
}
void factor_rec(u64 n, map<u64,int>& fac){
    if(n == 1) return;
    if(isPrimeDet(n)){ fac[n]++; return; }
    u64 d = pollard(n);
    factor_rec(d, fac);
    factor_rec(n/d, fac);
}

vector<u64> values;

long long query_indices(const vector<int>& idx){
    cout << "0 " << idx.size();
    for(int id: idx){
        cout << ' ' << values[id];
    }
    cout << '\n';
    cout.flush();
    long long ans;
    if(!(cin >> ans)){
        // If interaction fails, exit to avoid infinite loop
        exit(0);
    }
    return ans;
}
long long query_two(u64 a, u64 b){
    cout << "0 2 " << a << ' ' << b << '\n';
    cout.flush();
    long long ans;
    if(!(cin >> ans)) exit(0);
    return ans;
}
long long query_union(const vector<int>& A, const vector<int>& B){
    cout << "0 " << (A.size()+B.size());
    for(int id: A) cout << ' ' << values[id];
    for(int id: B) cout << ' ' << values[id];
    cout << '\n';
    cout.flush();
    long long ans;
    if(!(cin >> ans)) exit(0);
    return ans;
}

pair<int,int> find_cross_pair(vector<int> A, vector<int> B, long long hB){
    // Ensure A is smaller side initially for efficiency
    if(A.size() > B.size()){
        swap(A,B);
        // hB remains collisions of B (now the larger one), so recompute
        hB = query_indices(B);
    }

    // Reduce A to single element
    while(A.size() > 1){
        int mid = (int)A.size() / 2;
        vector<int> A1(A.begin(), A.begin()+mid);
        vector<int> A2(A.begin()+mid, A.end());
        long long hA1 = query_indices(A1);
        long long hU1 = query_union(A1, B);
        long long cross1 = hU1 - hA1 - hB;
        if(cross1 > 0){
            A.swap(A1);
        }else{
            A.swap(A2);
        }
    }
    int aidx = A[0];

    // Now find matching element in B
    while(B.size() > 1){
        int mid = (int)B.size() / 2;
        vector<int> B1(B.begin(), B.begin()+mid);
        vector<int> B2(B.begin()+mid, B.end());
        long long hB1 = query_indices(B1);
        // union with single element A
        cout << "0 " << (B1.size()+1) << ' ' << values[aidx];
        for(int id: B1) cout << ' ' << values[id];
        cout << '\n';
        cout.flush();
        long long hU = 0;
        if(!(cin >> hU)) exit(0);
        long long cross1 = hU - hB1; // since h({aidx}) = 0
        if(cross1 > 0){
            B.swap(B1);
            hB = hB1;
        }else{
            B.swap(B2);
            // hB becomes unknown; compute for the new B
            hB = query_indices(B);
        }
    }
    int bidx = B[0];
    return {aidx, bidx};
}

pair<int,int> find_any_pair_in_subset(vector<int> T){
    // T is known to have at least one collision inside
    while(T.size() > 2){
        int mid = (int)T.size() / 2;
        vector<int> L(T.begin(), T.begin()+mid);
        vector<int> R(T.begin()+mid, T.end());
        long long hL = query_indices(L);
        long long hR = query_indices(R);
        if(hL > 0){
            T.swap(L);
        }else if(hR > 0){
            T.swap(R);
        }else{
            // Across halves
            long long hB = hR; // collisions inside R
            return find_cross_pair(L, R, hB);
        }
    }
    // Base cases: T size 2 or 3
    if(T.size() == 2){
        return {T[0], T[1]};
    }else if(T.size() == 3){
        // Try pairs
        long long c01 = query_two(values[T[0]], values[T[1]]);
        if(c01 > 0) return {T[0], T[1]};
        long long c02 = query_two(values[T[0]], values[T[2]]);
        if(c02 > 0) return {T[0], T[2]};
        // Must be 1-2
        return {T[1], T[2]};
    }else{
        // Should not reach
        return {T[0], T[0]};
    }
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Parameters
    const int M = 200000; // total elements
    values.resize(M);
    for(int i=0;i<M;i++){
        u64 v = rand_u64(1, 1000000000000000000ULL);
        values[i] = v;
    }

    // Initial query with all elements
    vector<int> allIdx(M);
    iota(allIdx.begin(), allIdx.end(), 0);
    long long hAll = query_indices(allIdx);
    if(hAll <= 0){
        // As a fallback, increase m a bit and retry once
        // But problem constraints likely ensure positive; if not, just guess 2
        cout << "1 " << 2 << '\n';
        cout.flush();
        return 0;
    }

    // Choose subset B size based on collisions to have good chance cross>0
    // b ~ 1.5 * M / hAll, with bounds
    int b = (int)ceil(1.5 * (double)M / max(1LL, hAll));
    b = max(5000, min(20000, b));
    if(b > M/2) b = M/2;
    int a = M - b;

    // Build random partition A and B
    vector<int> idx(M);
    iota(idx.begin(), idx.end(), 0);
    shuffle(idx.begin(), idx.end(), rng);
    vector<int> Bidx(idx.begin(), idx.begin()+b);
    vector<int> Aidx(idx.begin()+b, idx.end());

    // Compute h(B)
    long long hB = query_indices(Bidx);

    // Ensure there is at least one cross pair between A and B
    // We'll attempt splitting assuming cross>0; if not, resample a few times
    long long crossAB = -1;
    int attempts = 0;
    while(attempts < 3){
        // We can avoid h(A) to reduce cost; assume cross>0 with chosen b
        // But to confirm, compute union and derive cross using h(B) and unknown h(A) - not possible
        // So we rely on chance; if later steps fail to find pair, we will resample
        // For safer check, compute cross via:
        // cross(A,B) = hAll - h(A) - h(B)
        long long hA = query_indices(Aidx);
        crossAB = hAll - hA - hB;
        if(crossAB > 0) break;
        // Resample
        shuffle(idx.begin(), idx.end(), rng);
        Bidx.assign(idx.begin(), idx.begin()+b);
        Aidx.assign(idx.begin()+b, idx.end());
        hB = query_indices(Bidx);
        attempts++;
    }
    if(crossAB <= 0){
        // As fallback, try to find a subset T of moderate size with internal collisions
        int gprime = max(6000, min(20000, (int)ceil(2.0 * M / max(1LL, hAll))));
        vector<int> sampleIdx;
        for(int tries=0; tries<5; ++tries){
            sampleIdx.clear();
            sampleIdx.reserve(gprime);
            unordered_set<int> used;
            while((int)sampleIdx.size() < gprime){
                int id = (int)rand_u64(0, M-1);
                if(used.insert(id).second) sampleIdx.push_back(id);
            }
            long long hT = query_indices(sampleIdx);
            if(hT > 0){
                auto pr = find_any_pair_in_subset(sampleIdx);
                int i = pr.first, j = pr.second;
                u64 d = values[i] > values[j] ? values[i]-values[j] : values[j]-values[i];
                if(d == 0){
                    // Extremely unlikely, pick different pair
                    // Guess 2 as fallback
                    cout << "1 " << 2 << '\n';
                    cout.flush();
                    return 0;
                }
                // Factor d and reduce to n
                map<u64,int> fac;
                factor_rec(d, fac);
                u64 cand = d;
                for(auto &kv: fac){
                    u64 p = kv.first;
                    int e = kv.second;
                    for(int t=0;t<e;t++){
                        u64 cand2 = cand / p;
                        if(cand2 == 0) break;
                        if(cand2+1 > 1000000000000000000ULL) break;
                        long long c = query_two(1, 1 + cand2);
                        if(c == 1){
                            cand = cand2;
                        }else{
                            break;
                        }
                    }
                }
                cout << "1 " << cand << '\n';
                cout.flush();
                return 0;
            }
        }
        // If still fail, guess 2
        cout << "1 " << 2 << '\n';
        cout.flush();
        return 0;
    }

    // Find a specific colliding pair across A and B
    auto pr = find_cross_pair(Aidx, Bidx, hB);
    int i = pr.first, j = pr.second;
    u64 d = values[i] > values[j] ? values[i]-values[j] : values[j]-values[i];
    if(d == 0){
        // Shouldn't happen
        cout << "1 " << 2 << '\n';
        cout.flush();
        return 0;
    }

    // Factor d and reduce to n using minimal divisibility tests
    map<u64,int> fac;
    factor_rec(d, fac);
    u64 cand = d;
    for(auto &kv: fac){
        u64 p = kv.first;
        int e = kv.second;
        for(int t=0;t<e;t++){
            u64 cand2 = cand / p;
            if(cand2 == 0) break;
            if(cand2 + 1 > 1000000000000000000ULL) break;
            long long c = query_two(1, 1 + cand2);
            if(c == 1){
                cand = cand2;
            }else{
                break;
            }
        }
    }

    cout << "1 " << cand << '\n';
    cout.flush();
    return 0;
}