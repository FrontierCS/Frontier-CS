#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if(!(cin >> N)) return 0;
    vector<long long> A(N+1), B(N+1);
    for(int i=1;i<=N;i++) cin >> A[i];
    for(int i=1;i<=N;i++) cin >> B[i];
    long long sumA = 0, sumB = 0;
    for(int i=1;i<=N;i++){ sumA += A[i]; sumB += B[i]; }
    if(sumA != sumB){
        cout << "No\n";
        return 0;
    }
    if(N == 2){
        if(A[1] == B[1] && A[2] == B[2]){
            cout << "Yes\n0\n";
            return 0;
        }
        long long t1 = A[2] - 1;
        long long t2 = A[1] + 1;
        if(t1 == B[1] && t2 == B[2]){
            cout << "Yes\n1\n1 2\n";
            return 0;
        }
        cout << "No\n";
        return 0;
    }
    // For N >= 3: construct sequence using identity-preserving transfers.
    vector<pair<int,int>> ops;

    auto add_op = [&](int i, int j){
        if(i > j) swap(i,j);
        ops.emplace_back(i,j);
    };

    // A(s,m,l): yields d = e_s - e_m, P=I on {s,m,l}
    auto add_A = [&](int s, int m, int l){
        add_op(s,m);
        add_op(m,l);
        add_op(s,l);
        add_op(m,l);
    };
    // reverse of A: d = e_m - e_s
    auto add_rA = [&](int s, int m, int l){
        add_op(m,l);
        add_op(s,l);
        add_op(m,l);
        add_op(s,m);
    };
    // B(s,m,l): yields d = e_s - e_l
    auto add_B = [&](int s, int m, int l){
        add_op(m,l);
        add_op(s,m);
        add_op(m,l);
        add_op(s,l);
    };
    // reverse of B: d = e_l - e_s
    auto add_rB = [&](int s, int m, int l){
        add_op(s,l);
        add_op(m,l);
        add_op(s,m);
        add_op(m,l);
    };

    // Transfer one unit from j -> i using helper k (distinct), updates A immediately.
    auto transfer = [&](int i, int j, int k){
        // i: dest, j: source, k: helper
        // sort s < m < l
        int s = i, m = j, l = k;
        vector<int> v = {i,j,k};
        sort(v.begin(), v.end());
        s = v[0]; m = v[1]; l = v[2];
        // determine which case (i,j)
        if(i==s && j==m){
            add_A(s,m,l);
        }else if(i==m && j==s){
            add_rA(s,m,l);
        }else if(i==s && j==l){
            add_B(s,m,l);
        }else if(i==l && j==s){
            add_rB(s,m,l);
        }else if(i==m && j==l){
            // e_m - e_l = (e_s - e_l) + (e_m - e_s) => B + rA
            add_B(s,m,l);
            add_rA(s,m,l);
        }else if(i==l && j==m){
            // e_l - e_m = (e_l - e_s) + (e_s - e_m) => rB + A
            add_rB(s,m,l);
            add_A(s,m,l);
        }else{
            // should not happen
        }
        A[i] += 1;
        A[j] -= 1;
    };

    auto choose_helper = [&](int x, int y){
        for(int h=1; h<=N; ++h){
            if(h!=x && h!=y) return h;
        }
        return 1; // never reached for N>=3
    };

    int pivot = N; // choose last index as pivot
    // Phase 1: move surplus from j to pivot
    for(int j=1;j<=N;j++){
        if(j==pivot) continue;
        long long d = A[j] - B[j];
        while(d > 0){
            int h = choose_helper(pivot, j);
            transfer(pivot, j, h); // move 1 from j to pivot
            d--;
        }
    }
    // Phase 2: fill deficits from pivot to j
    for(int j=1;j<=N;j++){
        if(j==pivot) continue;
        long long d = B[j] - A[j];
        while(d > 0){
            int h = choose_helper(j, pivot);
            transfer(j, pivot, h); // move 1 from pivot to j
            d--;
        }
    }
    // Now A should equal B
    bool ok = true;
    for(int i=1;i<=N;i++){
        if(A[i] != B[i]) { ok = false; break; }
    }
    if(!ok){
        // As a fallback (shouldn't happen), say No
        cout << "No\n";
        return 0;
    }
    cout << "Yes\n";
    cout << ops.size() << "\n";
    for(auto &p: ops){
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}