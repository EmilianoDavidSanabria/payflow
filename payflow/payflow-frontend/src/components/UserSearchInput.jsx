import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import UserSearchInput from "../components/UserSearchInput.jsx";

function UserSearchInput({ value, onSelect }) {
  const [query, setQuery] = useState(value || "");
  const [results, setResults] = useState([]);
  const [showResults, setShowResults] = useState(false);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    setQuery(value || "");
  }, [value]);

  useEffect(() => {
    const delay = setTimeout(async () => {
      const trimmed = query.trim();

      if (!trimmed) {
        setResults([]);
        setShowResults(false);
        setLoading(false);
        return;
      }

      try {
        setLoading(true);

        const response = await api.get("/users/search", {
          params: { q: trimmed },
        });

        setResults(response.data);
        setShowResults(true);
      } catch (error) {
        console.error("USER SEARCH ERROR:", error);
        setResults([]);
        setShowResults(false);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(delay);
  }, [query]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (!containerRef.current?.contains(event.target)) {
        setShowResults(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleSelect = (username) => {
    setQuery(username);
    setShowResults(false);
    onSelect(username);
  };

  return (
    <div className="autocomplete-wrapper" ref={containerRef}>
      <input
        className="input"
        type="text"
        value={query}
        placeholder="Search user by username"
        onChange={(e) => {
          const newValue = e.target.value;
          setQuery(newValue);
          onSelect(newValue);
        }}
        onFocus={() => {
          if (results.length > 0) {
            setShowResults(true);
          }
        }}
        autoComplete="off"
      />

      {showResults && (
        <div className="autocomplete">
          {loading ? (
            <div className="autocomplete-item autocomplete-item-muted">
              Searching users...
            </div>
          ) : results.length > 0 ? (
            results.map((user) => (
              <button
                key={user.id}
                type="button"
                className="autocomplete-item"
                onClick={() => handleSelect(user.username)}
              >
                @{user.username}
              </button>
            ))
          ) : (
            <div className="autocomplete-item autocomplete-item-muted">
              No users found
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default UserSearchInput;