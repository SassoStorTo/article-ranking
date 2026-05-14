import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";

import { createCorpus } from "../api/client";

export function NewCorpusPage({ onCreated }: { onCreated: (id: string) => void }) {
  return (
    <section className="single-page" aria-labelledby="new-corpus-title">
      <div className="page-heading">
        <p className="eyebrow">Create</p>
        <h2 id="new-corpus-title">Create Article Set</h2>
        <p className="muted">
          Start with an event name, then add article text or JSON files in the
          article set workspace.
        </p>
      </div>
      <NewCorpusForm onCreated={onCreated} />
    </section>
  );
}

function NewCorpusForm({ onCreated }: { onCreated: (id: string) => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [notes, setNotes] = useState("");
  const mutation = useMutation({
    mutationFn: createCorpus,
    onSuccess: async ({ id }) => {
      setName("");
      setNotes("");
      await queryClient.invalidateQueries({ queryKey: ["corpora"] });
      onCreated(id);
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    mutation.mutate({ name, notes: notes || undefined });
  }

  return (
    <form className="new-corpus" onSubmit={handleSubmit}>
      <label>
        Name
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          required
          maxLength={200}
        />
      </label>
      <label>
        Notes
        <textarea
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          rows={3}
        />
      </label>
      <button type="submit" disabled={mutation.isPending || !name.trim()}>
        Create Article Set
      </button>
      {mutation.error && <p className="error-line">{mutation.error.message}</p>}
    </form>
  );
}
