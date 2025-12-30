#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <set>
#include <vector>

// -------- Start of nlohmann/json.hpp --------
/*
    __ _____ _____ _____
 __|  |   __|     |   | |  JSON for Modern C++
|  |  |__   |  |  | | | |  version 3.11.3
|_____|_____|_____|_|___|  https://github.com/nlohmann/json

Licensed under the MIT License <http://opensource.org/licenses/MIT>.
SPDX-License-Identifier: MIT
Copyright (c) 2013-2023 Niels Lohmann <https://nlohmann.me>.

Permission is hereby  granted, free of charge, to any  person obtaining a copy
of this software and associated  documentation files (the "Software"), to deal
in the Software  without restriction, including without  limitation the rights
to  use, copy,  modify, merge,  publish, distribute,  sublicense, and/or  sell
copies  of  the Software,  and  to  permit persons  to  whom  the Software  is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE  IS PROVIDED "AS  IS", WITHOUT WARRANTY  OF ANY KIND,  EXPRESS OR
IMPLIED,  INCLUDING BUT  NOT  LIMITED TO  THE  WARRANTIES OF  MERCHANTABILITY,
FITNESS FOR  A PARTICULAR PURPOSE AND  NONINFRINGEMENT. IN NO EVENT  SHALL THE
AUTHORS  OR COPYRIGHT  HOLDERS  BE  LIABLE FOR  ANY  CLAIM,  DAMAGES OR  OTHER
LIABILITY, WHETHER IN AN ACTION OF  CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE  OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
*/
#include <nlohmann/json.hpp>
// -------- End of nlohmann/json.hpp --------


using json = nlohmann::json;

struct Item {
    std::string id;
    int w, h;
    long long v;
    int limit;
};

struct Placement {
    std::string id;
    int x, y, rot;
};

class SegTree {
private:
    std::vector<int> tree;
    std::vector<int> lazy;
    int n;

    void push(int node, int start, int end) {
        if (lazy[node] != -1) {
            tree[node] = lazy[node];
            if (start != end) {
                lazy[2 * node] = lazy[node];
                lazy[2 * node + 1] = lazy[node];
            }
            lazy[node] = -1;
        }
    }

    void update_range(int node, int start, int end, int l, int r, int val) {
        push(node, start, end);
        if (start > end || start > r || end < l) {
            return;
        }
        if (l <= start && end <= r) {
            lazy[node] = val;
            push(node, start, end);
            return;
        }
        int mid = start + (end - start) / 2;
        update_range(2 * node, start, mid, l, r, val);
        update_range(2 * node + 1, mid + 1, end, l, r, val);
        tree[node] = std::max(tree[2 * node], tree[2 * node + 1]);
    }

    int query_range(int node, int start, int end, int l, int r) {
        if (start > end || start > r || end < l) {
            return 0;
        }
        push(node, start, end);
        if (l <= start && end <= r) {
            return tree[node];
        }
        int mid = start + (end - start) / 2;
        int p1 = query_range(2 * node, start, mid, l, r);
        int p2 = query_range(2 * node + 1, mid + 1, end, l, r);
        return std::max(p1, p2);
    }

public:
    SegTree(int size) : n(size) {
        tree.assign(4 * n, 0);
        lazy.assign(4 * n, -1);
    }

    void update(int l, int r, int val) {
        if (l > r) return;
        update_range(1, 0, n - 1, l, r, val);
    }

    int query(int l, int r) {
        if (l > r) return 0;
        return query_range(1, 0, n - 1, l, r);
    }
};

int W, H;
bool allow_rotate;
std::vector<Item> items;
std::vector<Placement> placements;

void solve() {
    SegTree skyline(W);
    std::set<int> x_coords;
    x_coords.insert(0);
    x_coords.insert(W);

    std::vector<int> limits;
    for(const auto& item : items) {
        limits.push_back(item.limit);
    }

    while (true) {
        int best_item_idx = -1;
        int best_rot = -1;
        int best_x = -1, best_y = -1;
        long long max_v = -1;

        for (size_t i = 0; i < items.size(); ++i) {
            if (limits[i] == 0) continue;

            for (int rot = 0; rot < 2; ++rot) {
                if (rot == 1 && !allow_rotate) continue;

                int w = (rot == 0) ? items[i].w : items[i].h;
                int h = (rot == 0) ? items[i].h : items[i].w;

                if (w > W || h > H) continue;

                int current_best_x = -1, current_best_y = H + 1;

                std::set<int> candidate_x;
                for (int x_coord : x_coords) {
                    candidate_x.insert(x_coord);
                    if (x_coord >= w) {
                        candidate_x.insert(x_coord - w);
                    }
                }

                for (int x : candidate_x) {
                    if (x + w > W) continue;
                    
                    int y_base = skyline.query(x, x + w - 1);
                    if (y_base + h <= H) {
                        if (y_base < current_best_y) {
                            current_best_y = y_base;
                            current_best_x = x;
                        } else if (y_base == current_best_y) {
                            if (current_best_x == -1 || x < current_best_x) {
                                current_best_x = x;
                            }
                        }
                    }
                }
                
                if (current_best_x != -1) {
                    if (items[i].v > max_v) {
                        max_v = items[i].v;
                        best_item_idx = i;
                        best_rot = rot;
                        best_x = current_best_x;
                        best_y = current_best_y;
                    } else if (items[i].v == max_v) {
                        if (best_y == -1 || current_best_y < best_y) {
                            best_item_idx = i;
                            best_rot = rot;
                            best_x = current_best_x;
                            best_y = current_best_y;
                        } else if (current_best_y == best_y && (best_x == -1 || current_best_x < best_x)) {
                            best_item_idx = i;
                            best_rot = rot;
                            best_x = current_best_x;
                            best_y = current_best_y;
                        }
                    }
                }
            }
        }

        if (best_item_idx == -1) {
            break;
        }

        int w = (best_rot == 0) ? items[best_item_idx].w : items[best_item_idx].h;
        int h = (best_rot == 0) ? items[best_item_idx].h : items[best_item_idx].w;

        placements.push_back({items[best_item_idx].id, best_x, best_y, best_rot});
        skyline.update(best_x, best_x + w - 1, best_y + h);
        limits[best_item_idx]--;
        x_coords.insert(best_x);
        if (best_x + w <= W) {
            x_coords.insert(best_x + w);
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    json input;
    std::cin >> input;

    W = input["bin"]["W"];
    H = input["bin"]["H"];
    allow_rotate = input["bin"]["allow_rotate"];

    for (const auto& item_json : input["items"]) {
        items.push_back({
            item_json["type"],
            item_json["w"],
            item_json["h"],
            item_json["v"],
            item_json["limit"]
        });
    }

    solve();

    json output;
    output["placements"] = json::array();
    for (const auto& p : placements) {
        output["placements"].push_back({
            {"type", p.id},
            {"x", p.x},
            {"y", p.y},
            {"rot", p.rot}
        });
    }

    std::cout << output.dump() << std::endl;

    return 0;
}