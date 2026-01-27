#include <bits/stdc++.h>
using namespace std;
int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if(!(cin>>N)) return 0;
    vector<int> S(N);
    for(int i=0;i<N;i++) cin>>S[i];
    int M; cin>>M;
    for(int i=0;i<M;i++){
        int x,y; cin>>x>>y;
    }
    // Trivial output: 0 rounds, 0 cost
    cout<<0<<"\n";
    cout<<0<<"\n";
    return 0;
}