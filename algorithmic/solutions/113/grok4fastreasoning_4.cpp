#include <bits/stdc++.h>
using namespace std;

int N;
vector<int> basket[3];
vector<pair<int, int>> moves;

int get_center(vector<int> v) {
  if (v.empty()) return -1;
  sort(v.begin(), v.end());
  int s = v.size();
  int p = s / 2 + 1;
  return v[p - 1];
}

int count_less(const vector<int>& v, int ball) {
  int cnt = 0;
  for (int x : v) if (x < ball) cnt++;
  return cnt;
}

bool can_move(int from, int to, int ball) {
  vector<int> v = basket[to - 1];
  int sb = v.size();
  int p = sb / 2 + 1;
  int req_l = p - 1;
  int l = count_less(v, ball);
  return l == req_l;
}

void do_move(int from, int to) {
  vector<int> &fv = basket[from - 1];
  int ball = get_center(fv);
  fv.erase(remove(fv.begin(), fv.end(), ball), fv.end());

  if (can_move(from, to, ball)) {
    basket[to - 1].push_back(ball);
    moves.push_back({from, to});
    return;
  }

  // adjustment
  int third = 6 - from - to;
  // park center of to to third
  do_move(to, third);

  // now plain
  vector<int> &ff = basket[from - 1];
  ball = get_center(ff);
  assert(can_move(from, to, ball));
  ff.erase(remove(ff.begin(), ff.end(), ball), ff.end());
  basket[to - 1].push_back(ball);
  moves.push_back({from, to});

  // unpark
  do_move(third, to);
}

void transfer(int from, int to, int aux) {
  vector<int> &f = basket[from - 1];
  int s = f.size();
  if (s == 0) return;
  if (s == 1) {
    do_move(from, to);
    return;
  }
  do_move(from, aux);
  transfer(from, to, aux);
  do_move(aux, to);
  // repeat if needed
  transfer(from, to, aux);
}

int main() {
  cin >> N;
  for (int i = 1; i <= N; i++) basket[0].push_back(i);
  if (N > 0) transfer(1, 2, 3);
  if (N > 0) do_move(1, 3);
  if (N > 1) transfer(2, 3, 1);
  cout << moves.size() << endl;
  for (auto p : moves) {
    cout << p.first << " " << p.second << endl;
  }
  return 0;
}