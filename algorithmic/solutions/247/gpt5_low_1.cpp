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
    // Greedy: set positions from left to right, using one operation per mismatch if possible
    for(int i=1;i<=N-1;i++){
        if(A[i]==B[i]) continue;
        int need = B[i]+1;
        int j=-1;
        for(int k=i+1;k<=N;k++){
            if(A[k]==need){ j=k; break; }
        }
        if(j==-1){
            cout << "No\n";
            return 0;
        }
        // perform operation (i,j): Ai <- Aj-1, Aj <- Ai+1
        int Ai=A[i], Aj=A[j];
        A[i]=Aj-1;
        A[j]=Ai+1;
        ops.emplace_back(i,j);
    }
    if(A!=B){
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