#include <bits/stdc++.h>
using namespace std;

int main() {
  int n;
  cin >> n;
  vector<int> order;
  deque<int> deq;
  for (int i = 1; i <= n; i++) deq.push_back(i);
  bool take_left = true;
  while (!deq.empty()) {
    int x;
    if (take_left) {
      x = deq.front();
      deq.pop_front();
    } else {
      x = deq.back();
      deq.pop_back();
    }
    order.push_back(x);
    take_left = !take_left;
  }
  vector<int> basket(n + 1, 0);
  for (int i = 1; i <= n; i++) basket[i] = 1;
  vector<pair<int, int>> moves;
  set<int> added;
  auto get_center = [&](int b) -> int {
    int pop = 0;
    for (int i = 1; i <= n; i++)
      if (basket[i] == b) pop++;
    if (pop == 0) return 0;
    int pos = (pop + 2) / 2;
    int count = 0;
    for (int i = 1; i <= n; i++)
      if (basket[i] == b) {
        count++;
        if (count == pos) return i;
      }
    return 0;
  };
  auto can_move_func = [&](int from, int to) -> bool {
    int x = get_center(from);
    if (x == 0) return false;
    int pop_to = 0;
    int sm = 0;
    for (int i = 1; i <= n; i++)
      if (basket[i] == to) {
        pop_to++;
        if (i < x) sm++;
      }
    int needed = (pop_to + 1) / 2;
    if (sm == needed) {
      basket[x] = to;
      moves.emplace_back(from, to);
      return true;
    }
    return false;
  };
  for (int x : order) {
    int s = basket[x];
    int u = 6 - s - 3;
    while (get_center(s) != x) {
      int c = get_center(s);
      if (can_move_func(s, u)) {
        // done
      } else {
        while (true) {
          int cu = get_center(u);
          if (cu == 0 || added.count(cu)) break;
          can_move_func(u, 3);
        }
        can_move_func(s, u);
      }
    }
    while (true) {
      int ct = get_center(3);
      if (ct == 0 || added.count(ct)) break;
      can_move_func(3, u);
    }
    can_move_func(s, 3);
    added.insert(x);
  }
  cout << moves.size() << endl;
  for (auto p : moves) {
    cout << p.first << " " << p.second << endl;
  }
  return 0;
}