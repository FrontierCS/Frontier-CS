#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  int n;
  cin >> n;
  vector<char> in_s(n + 2, 0);
  vector<pair<int, int>> current;
  for (int i = 1; i <= n; ++i) {
    current.emplace_back(i, 0);
  }
  int queries = 0;
  int guesses = 0;
  const int MAX_Q = 53;
  const int MAX_G = 2;
  while (true) {
    size_t total = current.size();
    if (total == 0) {
      // impossible
      return 1;
    }
    if (total == 1 || (total == 2 && guesses < MAX_G)) {
      size_t idx = 0;
      int g = current[idx].first;
      cout << "! " << g << '\n';
      cout.flush();
      string resp;
      cin >> resp;
      if (resp == ":)") {
        return 0;
      }
      // wrong
      ++guesses;
      if (guesses > MAX_G) {
        // impossible
        return 1;
      }
      // remove guessed
      current.erase(current.begin() + idx);
      continue;
    } else {
      if (queries >= MAX_Q) {
        // impossible, guess one
        int g = current[0].first;
        cout << "! " << g << '\n';
        cout.flush();
        string resp;
        cin >> resp;
        if (resp == ":)") return 0;
        return 1;
      }
      vector<int> free_x, forced_x;
      for (auto& p : current) {
        if (p.second == 0) {
          free_x.push_back(p.first);
        } else {
          forced_x.push_back(p.first);
        }
      }
      int fsz = free_x.size();
      int fosz = forced_x.size();
      vector<int> s_elements;
      if (fosz == 0) {
        int half = fsz / 2;
        s_elements.resize(half);
        for (int i = 0; i < half; ++i) {
          s_elements[i] = free_x[i];
        }
      } else {
        int half = fosz / 2;
        s_elements.resize(half);
        for (int i = 0; i < half; ++i) {
          s_elements[i] = forced_x[i];
        }
        if (s_elements.empty() && fosz > 0) {
          s_elements.push_back(forced_x[0]);
        }
      }
      // ensure non-empty
      if (s_elements.empty() && fsz > 0) {
        s_elements.push_back(free_x[0]);
      }
      // print
      cout << "? " << s_elements.size();
      for (int val : s_elements) {
        cout << " " << val;
      }
      cout << '\n';
      cout.flush();
      string ans;
      cin >> ans;
      bool is_yes = (ans == "YES");
      int ay = is_yes ? 1 : 0;
      // set in_s
      for (int val : s_elements) {
        in_s[val] = 1;
      }
      // build new
      vector<pair<int, int>> new_curr;
      // free
      for (int x : free_x) {
        int t = in_s[x];
        int l2 = t ^ ay;
        new_curr.emplace_back(x, l2);
      }
      // forced
      for (int x : forced_x) {
        int t = in_s[x];
        if ((t ^ ay) == 0) {
          new_curr.emplace_back(x, 0);
        }
      }
      // reset in_s
      for (int val : s_elements) {
        in_s[val] = 0;
      }
      current = std::move(new_curr);
      ++queries;
    }
  }
  return 0;
}