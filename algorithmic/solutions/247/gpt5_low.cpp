#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if(!(cin >> N)) return 0;
    vector<int> A(N+1), B(N+1);
    for(int i=1;i<=N;i++) cin >> A[i];
    for(int i=1;i<=N;i++) cin >> B[i];

    long long sumA=0,sumB=0;
    for(int i=1;i<=N;i++){ sumA+=A[i]; sumB+=B[i]; }
    if(sumA!=sumB){
        cout << "No\n";
        return 0;
    }

    vector<pair<int,int>> ops;
    auto add_op = [&](int i, int j){
        if(i>j) swap(i,j);
        ops.emplace_back(i,j);
        // Apply to A to keep it consistent (optional but safe)
        int Ai = A[i], Aj = A[j];
        A[i] = Aj - 1;
        A[j] = Ai + 1;
    };

    if(N==1){
        if(A[1]==B[1]){
            cout << "Yes\n0\n";
        }else{
            cout << "No\n";
        }
        return 0;
    }
    if(N==2){
        if(A==B){
            cout << "Yes\n0\n";
            return 0;
        }else{
            // One operation (1,2) leads to (A2-1, A1+1)
            int x = A[2]-1, y = A[1]+1;
            if(x==B[1] && y==B[2]){
                cout << "Yes\n1\n1 2\n";
                return 0;
            }else{
                cout << "No\n";
                return 0;
            }
        }
    }

    // N >= 3
    // We can always make it by unit transfers using a helper index.
    // Prepare deficits and surpluses
    vector<long long> need(N+1,0);
    long long pos_sum = 0;
    for(int i=1;i<=N;i++){
        need[i] = (long long)B[i] - (long long)A[i];
        if(need[i] > 0) pos_sum += need[i];
    }

    // Helper function to transfer 1 unit from p to q using helper h (distinct from p,q)
    auto transfer_one = [&](int p, int q, int h){
        // Swap p and q via helper h: (p,h), (q,h), (p,h)
        add_op(p,h);
        add_op(q,h);
        add_op(p,h);
        // Then adjust with (p,q)
        add_op(p,q);
    };

    // Choose a default helper index
    int helper_default = N;

    // Build lists
    queue<pair<int,long long>> pos, neg;
    for(int i=1;i<=N;i++){
        if(need[i] > 0) pos.emplace(i, need[i]);
        else if(need[i] < 0) neg.emplace(i, -need[i]);
    }

    while(!pos.empty() && !neg.empty()){
        auto [pi, pa] = pos.front(); pos.pop();
        auto [ni, na] = neg.front(); neg.pop();
        long long take = min(pa, na);
        for(long long t=0; t<take; ++t){
            int h = helper_default;
            if(h==pi || h==ni){
                h = 1;
                if(h==pi || h==ni) h = 2; // since N>=3, 1 or 2 will be available
            }
            transfer_one(ni, pi, h); // move 1 from ni to pi
        }
        pa -= take; na -= take;
        if(pa > 0) pos.emplace(pi, pa);
        if(na > 0) neg.emplace(ni, na);
    }

    // After transfers, A should equal B
    if(A != B){
        // Fallback (should not happen), declare No
        cout << "No\n";
        return 0;
    }

    cout << "Yes\n";
    cout << ops.size() << "\n";
    for(auto &e: ops){
        cout << e.first << " " << e.second << "\n";
    }
    return 0;
}