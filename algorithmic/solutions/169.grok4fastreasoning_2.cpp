#include <bits/stdc++.h>
using namespace std;

int main() {
  int N;
  cin >> N;
  vector<string> board(N);
  for(int i=0; i<N; i++) cin >> board[i];
  vector<pair<int,int>> onis;
  for(int i=0; i<N; i++) for(int j=0; j<N; j++) if(board[i][j]=='x') onis.emplace_back(i,j);
  vector<pair<char,int>> moves;
  for(auto [r, c] : onis) {
    bool can_u = true, can_d=true, can_l=true, can_r=true;
    for(int k=0; k<r; k++) if(board[k][c]=='o') can_u = false;
    for(int k=r+1; k<N; k++) if(board[k][c]=='o') can_d = false;
    for(int k=0; k<c; k++) if(board[r][k]=='o') can_l = false;
    for(int k=c+1; k<N; k++) if(board[r][k]=='o') can_r = false;
    int dist_u = r+1;
    int dist_d = N - r;
    int dist_l = c+1;
    int dist_r = N - c;
    int cost_u = can_u ? 2 * dist_u : INT_MAX;
    int cost_d = can_d ? 2 * dist_d : INT_MAX;
    int cost_l = can_l ? 2 * dist_l : INT_MAX;
    int cost_r = can_r ? 2 * dist_r : INT_MAX;
    int minc = min({cost_u, cost_d, cost_l, cost_r});
    if(cost_u == minc) {
      for(int t=0; t<dist_u; t++) moves.emplace_back('U', c);
      for(int t=0; t<dist_u; t++) moves.emplace_back('D', c);
    } else if(cost_d == minc) {
      for(int t=0; t<dist_d; t++) moves.emplace_back('D', c);
      for(int t=0; t<dist_d; t++) moves.emplace_back('U', c);
    } else if(cost_l == minc) {
      for(int t=0; t<dist_l; t++) moves.emplace_back('L', r);
      for(int t=0; t<dist_l; t++) moves.emplace_back('R', r);
    } else {
      for(int t=0; t<dist_r; t++) moves.emplace_back('R', r);
      for(int t=0; t<dist_r; t++) moves.emplace_back('L', r);
    }
  }
  for(auto [d, p] : moves) {
    cout << d << " " << p << "\n";
  }
  return 0;
}