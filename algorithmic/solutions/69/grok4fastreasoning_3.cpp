#include <bits/stdc++.h>
using namespace std;

struct State {
  int len, link;
  int next[2];
  State() : len(0), link(-1), next{-1, -1} {}
};

long long compute_distinct(const string& a, const string& b) {
  vector<State> sam;
  sam.emplace_back(); // 0 root
  int last = 0;
  auto add = [&](int c) {
    sam.emplace_back();
    int cur = sam.size() - 1;
    sam[cur].len = sam[last].len + 1;
    int p = last;
    while (p != -1 && sam[p].next[c] == -1) {
      sam[p].next[c] = cur;
      p = sam[p].link;
    }
    if (p == -1) {
      sam[cur].link = 0;
    } else {
      int q = sam[p].next[c];
      if (sam[p].len + 1 == sam[q].len) {
        sam[cur].link = q;
      } else {
        sam.emplace_back();
        int clone = sam.size() - 1;
        sam[clone].len = sam[p].len + 1;
        sam[clone].link = sam[q].link;
        sam[clone].next[0] = sam[q].next[0];
        sam[clone].next[1] = sam[q].next[1];
        sam[q].link = clone;
        sam[cur].link = clone;
        int r = p;
        while (r != -1 && sam[r].next[c] == q) {
          sam[r].next[c] = clone;
          r = sam[r].link;
        }
      }
    }
    last = cur;
  };
  for (char ch : a) {
    int c = (ch == 'X' ? 0 : 1);
    add(c);
  }
  for (char ch : b) {
    int c = (ch == 'X' ? 0 : 1);
    add(c);
  }
  long long total = 0;
  for (size_t v = 1; v < sam.size(); ++v) {
    total += sam[v].len - sam[sam[v].link].len;
  }
  return total;
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n;
  cin >> n;
  vector<string> words(n + 1);
  for (int i = 1; i <= n; ++i) {
    words[i].resize(i);
    for (int k = 0; k < i; ++k) {
      words[i][k] = ((k + i) % 2 == 0 ? 'X' : 'O');
    }
  }
  for (int i = 1; i <= n; ++i) {
    cout << words[i] << '\n';
  }
  cout.flush();
  unordered_map<long long, pair<int, int>> mp;
  for (int i = 1; i <= n; ++i) {
    for (int j = 1; j <= n; ++j) {
      long long p = compute_distinct(words[i], words[j]);
      mp[p] = {i, j};
    }
  }
  int q;
  cin >> q;
  for (int qq = 0; qq < q; ++qq) {
    long long p;
    cin >> p;
    auto [u, v] = mp[p];
    cout << u << " " << v << '\n';
    cout.flush();
  }
  return 0;
}