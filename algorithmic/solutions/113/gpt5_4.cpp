#include <bits/stdc++.h>
using namespace std;

void hanoi(int n, int from, int to, int aux, vector<pair<int,int>>& moves){
    if(n==0) return;
    hanoi(n-1, from, aux, to, moves);
    moves.emplace_back(from, to);
    hanoi(n-1, aux, to, from, moves);
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if(!(cin >> N)) return 0;
    vector<pair<int,int>> moves;
    hanoi(N, 1, 3, 2, moves);
    cout << moves.size() << '\n';
    for(auto &p: moves){
        cout << p.first << ' ' << p.second << '\n';
    }
    return 0;
}