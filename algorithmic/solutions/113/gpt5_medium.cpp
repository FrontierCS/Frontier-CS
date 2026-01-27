#include <bits/stdc++.h>
using namespace std;

vector<int> B[4];
vector<pair<int,int>> movesLog;

int centerIndex(int a){
    int k = (int)B[a].size();
    // 1-based center index is (k+2)/2, convert to 0-based
    return (k + 2) / 2 - 1;
}

int centerBall(int a){
    return B[a][centerIndex(a)];
}

int countLess(int a, int x){
    return lower_bound(B[a].begin(), B[a].end(), x) - B[a].begin();
}

bool allowedAB(int a, int b){
    if(B[a].empty()) return false;
    int x = centerBall(a);
    int m = (int)B[b].size();
    int t = (m + 1) / 2;
    int less = countLess(b, x);
    return less == t;
}

void doMove(int a, int b){
    int idx = centerIndex(a);
    int x = B[a][idx];
    B[a].erase(B[a].begin() + idx);
    auto it = lower_bound(B[b].begin(), B[b].end(), x);
    B[b].insert(it, x);
    movesLog.emplace_back(a, b);
}

void ensureMoveOut(int b, int c, int a); // forward

void pushCenter(int a, int b, int c){
    if(B[a].empty()) return;
    while(!allowedAB(a, b)){
        ensureMoveOut(b, c, a);
    }
    doMove(a, b);
}

void ensureMoveOut(int b, int c, int a){
    if(B[b].empty()) return; // nothing to move out
    while(!allowedAB(b, c)){
        ensureMoveOut(c, a, b);
    }
    doMove(b, c);
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if(!(cin >> N)) return 0;
    B[1].clear(); B[2].clear(); B[3].clear();
    for(int i=1;i<=N;i++) B[1].push_back(i);

    // Move all to basket 3
    while(!B[1].empty() || !B[2].empty()){
        if(!B[1].empty()) pushCenter(1, 3, 2);
        else pushCenter(2, 3, 1);
    }

    cout << movesLog.size() << "\n";
    for(auto &p : movesLog){
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}